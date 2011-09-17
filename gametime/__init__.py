#!/usr/bin/python
import os

PROG_DIR = os.getcwd()
CSS_DIR = os.path.join(PROG_DIR, 'data/css')
JS_DIR = os.path.join(PROG_DIR, 'data/js')
IMAGES_DIR = os.path.join(PROG_DIR, 'data/images')
TMPL_DIR = os.path.join(PROG_DIR, 'data/interfaces/default')

DATABASE_FILENAME = 'gametime.s3db'
DATABASE_SCHEMA_FILENAME = 'gametime.schema.s3db'
