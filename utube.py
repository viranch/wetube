import socket, httplib, urllib, urllib2
import htmlentitydefs
import re
import os
import string
try:
	from urlparse import parse_qs
except ImportError:
	from cgi import parse_qs

std_headers = {
	'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.8) Gecko/20100723 Firefox/3.6.8',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Language': 'en-us,en;q=0.5',
}

_err = ['']
_VALID_URL = r'^((?:http://)?(?:youtu\.be/|(?:\w+\.)?youtube\.com/(?:(?:v/)|(?:(?:watch(?:_popup)?(?:\.php)?)?[\?#](?:.+&)?v=))))?([0-9A-Za-z_-]+)(?(1).+)?$'
simple_title_chars = string.ascii_letters.decode('ascii') + string.digits.decode('ascii')

# Listed in order of quality
_available_formats = ['38', '37', '22', '45', '35', '34', '43', '18', '6', '5', '17', '13']
_video_extensions = {
	'13': '3gp',
	'17': 'mp4',
	'18': 'mp4',
	'22': 'mp4',
	'37': 'mp4',
	'38': 'video', # You actually don't know if this will be MOV, AVI or whatever
	'43': 'webm',
	'45': 'webm',
}

def htmlentity_transform(matchobj):
	"""Transforms an HTML entity to a Unicode character.
	
	This function receives a match object and is intended to be used with
	the re.sub() function.
	"""
	entity = matchobj.group(1)

	# Known non-numeric HTML entity
	if entity in htmlentitydefs.name2codepoint:
		return unichr(htmlentitydefs.name2codepoint[entity])

	# Unicode character
	mobj = re.match(ur'(?u)#(x?\d+)', entity)
	if mobj is not None:
		numstr = mobj.group(1)
		if numstr.startswith(u'x'):
			base = 16
			numstr = u'0%s' % numstr
		else:
			base = 10
		return unichr(long(numstr, base))

	# Unknown entity in name, return its literal representation
	return (u'&%s;' % entity)

def sanitize_title(utitle):
	"""Sanitizes a video title so it could be used as part of a filename."""
	utitle = re.sub(ur'(?u)&(.+?);', htmlentity_transform, utitle)
	return utitle.replace(unicode(os.sep), u'%')

def valid (url):
	my_VALID_URL = r'(http://)?(www\.)?youtube\.com/watch/*\?v=.*'
	return (re.match(_VALID_URL, url) is not None and re.match(my_VALID_URL, url) is not None)

def get_video_id (url):
	# Extract video id from URL
	return re.match(_VALID_URL, url).group(2)

def get_video_info ( url ):
	# Extract video id from URL
	video_id = get_video_id (url)

	# Get video webpage
	request = urllib2.Request('http://www.youtube.com/watch?v=%s&gl=US&hl=en' % video_id, None, std_headers)
	try:
		video_webpage = urllib2.urlopen(request).read()
	except (urllib2.URLError, httplib.HTTPException, socket.error), err:
		#trouble(u'unable to download video webpage: %s' % str(err))
		video_webpage = None

	# Attempt to extract SWF player URL
	if video_webpage != None:
		mobj = re.search(r'swfConfig.*"(http://.*?watch.*?-.*?\.swf)"', video_webpage)
		if mobj is not None:
			player_url = mobj.group(1)
		else:
			player_url = None

	# Get video info
	for el_type in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
		video_info_url = ('http://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en'
					% (video_id, el_type))
		request = urllib2.Request(video_info_url, None, std_headers)
		try:
			video_info_webpage = urllib2.urlopen(request).read()
			video_info = parse_qs(video_info_webpage)
			if 'token' in video_info:
				break
		except (urllib2.URLError, httplib.HTTPException, socket.error), err:
			trouble(u'unable to download video info webpage: %s' % str(err))
			return
	if 'token' not in video_info:
		if 'reason' in video_info:
			trouble(u'YouTube said: %s' % video_info['reason'][0])
		else:
			trouble(u'"token" parameter not in video info for unknown reason')
		return

	# Start extracting information

	# uploader
	if 'author' not in video_info:
		video_uploader = 'Unknown'
		#trouble(u'unable to extract uploader nickname')
	else:
		video_uploader = urllib.unquote_plus(video_info['author'][0])

	# title
	if 'title' not in video_info:
		video_title = ''
	#	trouble(u'unable to extract video title')
	#	return
	else:
		video_title = urllib.unquote_plus(video_info['title'][0])
		video_title = video_title.decode('utf-8')

	# simplified title
	if video_title != '':
		simple_title = sanitize_title(video_title)
		simple_title = re.sub(ur'(?u)([^%s]+)' % simple_title_chars, ur'_', simple_title)
		simple_title = simple_title.strip(ur'_')
	else:
		simple_title = ''

	# thumbnail image
	if 'thumbnail_url' not in video_info:
	#	trouble(u'WARNING: unable to extract video thumbnail')
		video_thumbnail = ''
	else:	# don't panic if we can't find it
		video_thumbnail = urllib.unquote_plus(video_info['thumbnail_url'][0])

	# description
	video_description = 'No description available.'
	if video_webpage != None:
		mobj = re.search(r'<meta name="description" content="(.*)"(?:\s*/)?>', video_webpage)
		if mobj is not None:
			video_description = mobj.group(1)

	# token
	video_token = urllib.unquote_plus(video_info['token'][0])

	# Decide which formats to download
	get_video_template = 'http://www.youtube.com/get_video?video_id=%s&t=%s&eurl=&el=&ps=&asv=&fmt=%%s' % (video_id, video_token)

	if 'fmt_url_map' in video_info:
		url_map = dict(tuple(pair.split('|')) for pair in video_info['fmt_url_map'][0].split(','))
		existing_formats = [x for x in _available_formats if x in url_map]
		if len(existing_formats) == 0:
			trouble(u'no known formats available for video')
			return
		video_url_list = [(existing_formats[0], get_video_template % existing_formats[0])] # Best quality

	elif 'conn' in video_info and video_info['conn'][0].startswith('rtmp'):
		video_url_list = [(None, video_info['conn'][0])]

	else:
		trouble(u'no fmt_url_map or conn information found in video info')
		return

	for format_param, video_real_url in video_url_list:
		# Extension
		video_extension = _video_extensions.get(format_param, 'flv')

		# Find the video URL in fmt_url_map or conn paramters
#		try:
		# Process video information
		ret = {
			'vid_id':	video_id.decode('utf-8'),
			'url':		video_real_url.decode('utf-8'),
			'uploader':	video_uploader.decode('utf-8'),
			'title':	video_title,
			'stitle':	simple_title,
			'ext':		video_extension.decode('utf-8'),
			'format':	(format_param is None and u'NA' or format_param.decode('utf-8')),
			'thumbnail':	video_thumbnail.decode('utf-8'),
			'description':	video_description.decode('utf-8'),
			'player_url':	player_url,
		}
		return ret
#		except UnavailableVideoError, err:
#			trouble(u'unable to download video (format may not be available)')

def trouble ( err ):
	_err[0] = err

if __name__=='__main__':
	import sys
	desc = get_video_info ( sys.argv[1] )
	for key in desc.keys():
		print key, ':', desc[key]
