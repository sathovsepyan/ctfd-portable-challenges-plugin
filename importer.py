#!/usr/bin/env python2

from flask import Flask
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from werkzeug.utils import secure_filename

import json
import hashlib
import yaml
import shutil
import os
import sys
import hashlib
import argparse


REQ_FIELDS = ['name', 'description', 'value', 'category', 'flags']

def parse_args():
    parser = argparse.ArgumentParser(description='Import CTFd challenges and their attachments to a DB from a YAML formated specification file and an associated attachment directory')
    parser.add_argument('--app-root', dest='app_root', type=str, help="app_root directory for the CTFd Flask app (default: 2 directories up from this script)", default=None)
    parser.add_argument('-d', dest='db_uri', type=str, help="URI of the database where the challenges should be stored")
    parser.add_argument('-F', dest='dst_attachments', type=str, help="directory where challenge attachment files should be stored")
    parser.add_argument('-i', dest='in_file', type=str, help="name of the input YAML file (default: export.yaml)", default="export.yaml")
    parser.add_argument('--skip-on-error', dest="exit_on_error", action='store_false', help="If set, the importer will skip the importing challenges which have errors rather than halt.", default=True)
    parser.add_argument('--move', dest="move", action='store_true', help="if set the import proccess will move files rather than copy them", default=False)
    return parser.parse_args()

def process_args(args):
    if not (args.db_uri and args.dst_attachments):
        if args.app_root:
            app.root_path = os.path.abspath(args.app_root)
        else:
            abs_filepath = os.path.abspath(__file__)
            grandparent_dir = os.path.dirname(os.path.dirname(os.path.dirname(abs_filepath)))
            app.root_path = grandparent_dir
        sys.path.append(os.path.dirname(app.root_path))
        app.config.from_object("CTFd.config.Config")

    if args.db_uri:
        app.config['SQLALCHEMY_DATABASE_URI'] = args.db_uri
    if not args.dst_attachments:
        args.dst_attachments = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])

    return args

class MissingFieldError(Exception):
    def __init__(self, name):
        self.name = value
    def __str__(self):
        return "Error: Missing field '{}'".format(name)

def import_challenges(in_file, dst_attachments, exit_on_error=True, move=False):
    from CTFd.models import db, Challenges, Flags, Tags, ChallengeFiles
    from CTFd.utils import uploads
    chals = []
    with open(in_file, 'r') as in_stream:
        chals = yaml.safe_load_all(in_stream)

        for chal in chals:
            skip = False
            for req_field in REQ_FIELDS:
                if req_field not in chal:
                    if exit_on_error:
                        raise MissingFieldError(req_field)
                    else:
                        print "Skipping challenge: Missing field '{}'".format(req_field)
                        skip = True
                        break
            if skip:
                continue

            for flag in chal['flags']:
                if 'flag' not in flag:
                    if exit_on_error:
                        raise MissingFieldError('flag')
                    else:
                        print "Skipping flag: Missing field 'flag'"
                        continue
                flag['flag'] = flag['flag'].strip()
                if 'type' not in flag:
                    flag['type'] = "static"

            matching_chal = Challenges.query.filter_by(name=chal['name'].strip()).first()
            if matching_chal:
                print "Updating {}: Duplicate challenge found in DB (id: {})".format(chal['name'].encode('utf8'), matching_chal.id)
                Tags.query.filter_by(challenge_id=matching_chal.id).delete()
                ChallengeFiles.query.filter_by(challenge_id=matching_chal.id).delete()
                Flags.query.filter_by(challenge_id=matching_chal.id).delete()
                #Hints.query.filter_by(challenge_id=matching_chal.id).delete()

                matching_chal.name = chal['name'].strip()
                matching_chal.description = chal['description'].strip()
                matching_chal.category = chal['category'].strip()
                if chal.get('type', 'standard') == 'standard':
                    matching_chal.value = chal['value']

                db.session.commit()
                chal_dbobj = matching_chal

            else:
                print "Adding {}".format(chal['name'].encode('utf8'))

                chal_type = chal.get('type', 'standard')
                if chal_type == 'standard':
                    # We ignore traling and leading whitespace when importing challenges
                    chal_dbobj = Challenges(
                        name=chal['name'].strip(),
                        description=chal['description'].strip(),
                        value=chal['value'],
                        category=chal['category'].strip(),
                    )
                elif chal_type == 'dynamic':
                    from CTFd.plugins.dynamic_challenges import DynamicChallenge
                    # We ignore traling and leading whitespace when importing challenges
                    chal_dbobj = DynamicChallenge(
                        name=chal['name'].strip(),
                        description=chal['description'].strip(),
                        category=chal['category'].strip(),
                        value=int(chal['value']),
                        minimum=int(chal['minimum']),
                        decay=int(chal['decay']),
                    )
                else:
                    raise ValueError('Unknown type of challenge')

                db.session.add(chal_dbobj)
                db.session.commit()

            if 'tags' in chal:
                for tag in chal['tags']:
                    tag_dbobj = Tags(chal_dbobj.id, tag)
                    db.session.add(tag_dbobj)

            for flag in chal['flags']:
                flag_db = Flags(
                    challenge_id=chal_dbobj.id,
                    content=flag['flag'],
                    type=flag['type']
                )
                db.session.add(flag_db)


            if 'files' in chal:
                from io import FileIO
                for filename in chal['files']:
                    # upload_file takes a werkzeug.FileStorage object, but we can get close enough
                    # with a file object with a filename property added
                    filepath = os.path.join(os.path.dirname(in_file), filename)
                    with FileIO(filepath, mode='rb') as f:
                        f.filename = os.path.basename(f.name)
                        uploads.upload_file(file=f, challenge=chal_dbobj.id, type='challenge')

    db.session.commit()
    db.session.close()
        

if __name__ == "__main__":
    args = parse_args()
    
    app = Flask(__name__)


    with app.app_context():
        args = process_args(args)
        from CTFd.models import db

        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        url = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
        if url.drivername == 'postgres':
            url.drivername = 'postgresql'

        db.init_app(app)

        from CTFd.cache import cache
        cache.init_app(app)

        try:
            if not (url.drivername.startswith('sqlite') or database_exists(url)):
                create_database(url)
            db.create_all()
        except OperationalError:
            db.create_all()
        else:
            db.create_all()

        app.db = db
        import_challenges(args.in_file, args.dst_attachments, args.exit_on_error, move=args.move)
