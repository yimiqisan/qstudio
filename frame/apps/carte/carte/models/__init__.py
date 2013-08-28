# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from sqlalchemy import sql
from sqlalchemy.ext.hybrid import hybrid_property
from frame.platform.engines import db

__all__ = ['ChannelModel', 'ChannelStatisticsModel',
    'ShowModel', 'MarkdownModel']


class ChannelModel(db.Model):
    __tablename__ = 'channel'
    __table_args__ = (
        db.UniqueConstraint('ukey', 'name'),
        )

    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    ukey = db.Column(db.CHAR(6), nullable=False, index=True)
    name = db.Column(db.Unicode(256), nullable=False)
    introduction = db.Column(db.Unicode(1024), server_default='')
    template = db.Column(db.CHAR(128), index=True)
    sort_score = db.Column(db.Integer(), nullable=False)
    is_public = db.Column(db.Boolean(), nullable=False,
                             server_default=sql.true(), index=True)
    date_created = db.Column(db.DateTime(timezone=True),
                            nullable=False, index=True,
                            server_default=db.func.current_timestamp())

    shows = db.relationship(
        'ShowModel', lazy='dynamic', uselist=True,
        backref=db.backref('channel', lazy='joined', innerjoin=True),
        primaryjoin='ChannelModel.id==ShowModel.channel_id',
        foreign_keys='[ShowModel.channel_id]',
        order_by='desc(ShowModel.date_created)',
        passive_deletes='all')

    _statistics = db.relationship(
        'ChannelStatisticsModel',
        backref=db.backref('channel', lazy='joined', innerjoin=True),
        primaryjoin='ChannelModel.id==ChannelStatisticsModel.id',
        foreign_keys='[ChannelStatisticsModel.id]',
        uselist=False, passive_deletes='all')

    @hybrid_property
    def shows_count(self):
        try:
            return self._statistics.recommends_count
        except AttributeError:
            return 0

    @shows_count.setter
    def shows_count_setter(self, value):
        try:
            self._statistics.shows_count = value
        except AttributeError:
            self._statistics = ChannelStatisticsModel(shows_count=value)

    @shows_count.expression
    def shows_count_expr(cls):
        return ChannelStatisticsModel.shows_count

    def as_dict(self):
        return {'id': self.id,
                'ukey': self.ukey,
                'name': self.name,
                'introduction': self.introduction,
                'template': self.template,
                'sort_score': self.sort_score,
                'is_public': self.is_public,
                'shows_count': self.shows_count,
                'date_created': self.date_created.isoformat(),
                }


class ChannelStatisticsModel(db.Model):
    __tablename__ = 'channel_statistics'

    id = db.Column(db.Integer(), db.ForeignKey('channel.id'),
                   primary_key=True, nullable=False)
    shows_count = db.Column(db.Integer(), nullable=False,
                                 default=0, server_default='0')


class ShowModel(db.Model):
    __tablename__ = 'show'
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    chanel_id = db.Column(db.Integer(), db.ForeignKey('channel.id'),
                             nullable=False, index=True)
    title = db.Column(db.Unicode(256), nullable=False, unique=True)
    date_created = db.Column(db.DateTime(timezone=True),
                                nullable=False, index=True,
                                server_default=db.func.current_timestamp())


class MarkdownModel(db.Model):
    __tablename__ = 'show_markdown'

    id = db.Column(db.Integer(), db.ForeignKey('show.id'),
                   primary_key=True, nullable=False)
    markdown = db.Column(db.UnicodeText(), nullable=False, server_default='')
