#==============================================================================
# multiloggy_web - a Flask frontend for multiloggy logfiles
#
# Adapted from Sean B. Palmer's cgi script
# and Michael Yanovich's URL/syntax highlighting
# by Joan Touzet (@wohali) into a flask joint
#
# http://github.com/wohali/multiloggy
#
# Do with it as you will.
#==============================================================================
from flask import Flask, render_template, redirect, url_for, Markup
import codecs
import datetime
import glob
import os.path
import re
import time
import sys

#==============================================================================
# constants
#==============================================================================
app = Flask(__name__)
LOGDIR = os.path.normpath("{0}/../logs".format(
                          os.path.dirname(os.path.realpath(__file__))
                          ))
r_colour = re.compile(r'\x03(\d{1,2})(?:,(\d{1,2}))?')
r_bold = re.compile(r'\x02([^\x02]*?)\x02')
r_uri = re.compile(
    r'((ftp|https?)://([^\s<>"\'\[\]),;:.&]|&(?![gl]t;)|[\[\]),;:.](?! ))+)'
)
colours = {
        '01': 'black',
        '02': 'navy',
        '03': 'green',
        '04': 'red',
        '05': 'maroon',
        '06': 'purple',
        '07': 'olive',
        '08': 'yellow',
        '09': 'lime',
        '10': 'teal',
        '11': 'aqua',
        '12': 'blue',
        '13': 'fuchsia',
        '14': 'gray',
        '15': 'slate grey',
        }


#==============================================================================
# helpers
#==============================================================================
def _get_colour(matchobj):
    fg = matchobj.group(1)
    bg = matchobj.group(2)
    if not bg:
        if fg in colours:
            return '<span style="color:{0};">'.format(colours[fg])
    if bg in colours and fg in colours:
        return '<span style="color:{0}; background-color:{1}">' \
            .format(colours[fg], colours[bg])


def _get_bold(matchobj):
    tempstr = matchobj.group(0)
    base = '<span style="font-weight: bold;">%s</span>'
    result = r_bold.findall(tempstr)
    if result:
        return base % (result[0])


#==============================================================================
# flask bits
#==============================================================================
@app.route('/')
def top():
    channels = sorted((name for name in os.listdir(LOGDIR)
                       if os.path.isdir(os.path.join(LOGDIR, name))))
    return render_template('index.html',
                           org=ORGANIZATION,
                           link=WEBSITE,
                           channels=channels)


@app.route('/<channel>/')
def show_channel(channel):
    chanlogdir = os.path.join(LOGDIR, channel)
    if not os.path.isdir(chanlogdir):
        return redirect(url_for('top'))
    logs = list()
    filenames = glob.glob(os.path.join(chanlogdir, '*.txt'))
    filenames.sort(reverse=True)
    for fn in filenames:
        if not os.path.isfile(fn) or not os.access(fn, os.R_OK):
            continue
        log = dict()
        log['date'], dummy = os.path.splitext(os.path.basename(fn))
        log['size'] = os.stat(fn).st_size
        logs.append(log)
    return render_template('channel.html',
                           logs=logs,
                           channel=channel,
                           link=WEBSITE,
                           org=ORGANIZATION)


@app.route('/<channel>/<date>')
def show_channel_day(channel, date):
    eng_date = time.strftime('%d %B %Y',
                             time.strptime(date, '%Y-%m-%d'))
    if eng_date[0] == '0':
        eng_date = eng_date[1:]
    logfile = os.path.join(LOGDIR,
                           channel,
                           '{0}.txt'.format(date))

    lines = list()
    with codecs.open(logfile, 'r', 'utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            t, content = line.split(' ', 1)
            if content.startswith('***') and ('quit' in content):
                cls, (a, b) = 'quit', content[4:].split(' ', 1)
            elif content.startswith('***') and ('part' in content):
                cls, (a, b) = 'part', content[4:].split(' ', 1)
            elif content.startswith('***') and ('join' in content):
                cls, (a, b) = 'join', content[4:].split(' ', 1)
            elif content.startswith('***'):
                cls, a, b = 'event', '***', content[4:]
            elif content.startswith('*'):
                cls, (a, b) = 'action', content[2:].split(' ', 1)
                a = '* ' + a
            elif content.startswith('<'):
                cls, (a, b) = 'message', content.split(' ', 1)
            else:
                cls, a, b = 'unknown', '?', content

            fragid = 'T' + t.replace(':', '-')
            b, numspans = r_colour.subn(_get_colour, b)
            for dummy in range(0, numspans):
                b = b + "</span>"
            b = r_bold.sub(_get_bold, b)
            b = Markup(r_uri.sub(r'<a href="\1">\1</a>', b))
            lines.append((cls, fragid, t, a, b))

    return render_template('day.html',
                           day=eng_date,
                           channel=channel,
                           lines=lines,
                           link=WEBSITE,
                           org=ORGANIZATION)


@app.route('/<channel>/today')
def show_channel_today(channel):
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    return redirect(url_for('show_channel_day',
                            channel=channel,
                            date=today))

#==============================================================================
# Second Doctor is best doctor.
# -wohali
#==============================================================================

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: {0} <organization> <website>".format(sys.argv[0])
        sys.exit(1)
    ORGANIZATION = sys.argv[1]
    WEBSITE = sys.argv[2]
    app.run(debug=True)
