# -*- coding: utf-8 -*-
"""单元测试 frame.platform.base._flask_sqlalchemy 的模块"""
from __future__ import unicode_literals

import os
import time

from frame.platform.flask import Flask
from frame.platform.flask.testing import TestCase
from frame.platform.engines import db

class DBTestCase(TestCase):

    def create_app(self):
        app = Flask(__name__)
        runshm = os.path.isdir('/run/shm')
        devshm = os.path.isdir('/dev/shm')
        if runshm:
            dbpath = '/run/shm/dbtest.db'
        elif devshm:
            dbpath = '/dev/shm/dbtest.db'
        else:
            dbpath = '/tmp/dbtest.db'
        self.dbpath =dbpath

        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///%s' % dbpath,
            SQLALCHEMY_DATABASE_SLAVE_URIS=['sqlite:///%s' % dbpath]
        )

        db.init_app(app)

        return app

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        os.unlink(self.dbpath)

    def test_preserve_deleted(self):

        @db.preserve_deleted(
            db.Column('date_deleted', db.DateTime(timezone=True),
                      server_default=db.func.current_timestamp(),
                      nullable=False, index=True),
            reason=db.Column(db.String(10)))
        class A(db.Model):
            __tablename__ = 'a'

            id = db.Column(db.Integer(), primary_key=True)
            data1 = db.Column(db.String(256))
            data2 = db.Column(db.Text())

            def __eq__(self, other):
                return isinstance(other, A) and other.id == self.id and \
                       other.data1 == self.data1 and other.data2 == self.data2

        db.create_all()

        a1, a2 = \
            A(data1='a1d1', data2='a1d2'), \
            A(data1='a2d1', data2='a2d2')

        db.session.add_all([a1, a2])
        db.session.commit()

        self.assertEqual(A.query.order_by(A.id).all(), [a1, a2])

        db.session.delete(a1, reason='for_fun')
        db.session.commit()

        self.assertEqual(A.query.order_by(A.id).all(), [a2])

        a1_deleted = A.deleted.query.get(1)
        self.assertEqual(a1_deleted.data1, 'a1d1')
        self.assertEqual(a1_deleted.data2, 'a1d2')
        self.assertEqual(a1_deleted.reason, 'for_fun')
        # sqlite 的 current_timestamp 是 UTC 时区的, 最多能偏移一整天
        self.assertTrue(int(a1_deleted.date_deleted.strftime('%s')) + 86400 > time.time())

        a1_deleted.restore()
        db.session.commit()

        self.assertEqual(A.deleted.query.count(), 0)
        self.assertEqual(A.query.order_by(A.id).all(), [a1, a2])
