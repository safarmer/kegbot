from datetime import datetime
import time
import sys

from sqlobject import *

import units
import util

def setup(db_uri):
   """ Set default connection """
   connection = connectionForURI(db_uri)
   sqlhub.processConnection = connection

def drop_and_create(tbl):
   try:
      tbl.dropTable()
   except:
      pass
   tbl.createTable()


class Config(SQLObject):
   class sqlmeta:
      table = 'config'
      idType = str

   value = StringCol(notNone=True)

   def createTable(cls, ifNotExists=False, createJoinTables=True,
                   createIndexes=True,
                   connection=None):
      conn = connection or cls._connection
      if ifNotExists and conn.tableExists(cls.sqlmeta.table):
         return
      conn.query(cls.createTableSQL())
   createTable = classmethod(createTable)

   def createTableSQL(cls, createJoinTables=True, connection=None,
                      createIndexes=True):
      conn = connection or cls._connection
      q = """ CREATE TABLE `%s` (
              `%s` varchar(64) NOT NULL default '',
              `value` mediumtext NOT NULL,
              PRIMARY KEY  (`%s`)
      ) """ % (cls.sqlmeta.table, cls.sqlmeta.idName, cls.sqlmeta.idName)
      return q
   createTableSQL = classmethod(createTableSQL)


class Drink(SQLObject):
   class sqlmeta:
      table = 'drinks'
      lazyUpdate = True

   ticks = IntCol(default=0, notNone=True)
   volume = IntCol(default=0, notNone=True)
   starttime = IntCol(notNone=True)
   endtime = IntCol(notNone=True)
   user = ForeignKey('User', notNone=True)
   keg = ForeignKey('Keg', notNone=True)
   status = EnumCol(enumValues=['valid','invalid'], default='valid', notNone=True)


class Keg(SQLObject):
   class sqlmeta:
      table = 'kegs'
      lazyUpdate = True

   # default full_volume = 15.5 gallons in mL
   full_volume = IntCol(default=58673, notNone=True)
   startdate = DateTimeCol()
   enddate = DateTimeCol()
   status = EnumCol(enumValues=['online', 'offline', 'coming soon'], default='online')
   beername = StringCol(default='')
   alccontent = FloatCol(default=4.5)
   description = StringCol(default='')
   origcost = FloatCol(default=0)
   beerpalid = IntCol(default=0)
   ratebeerid = IntCol(default=0)
   calories_oz = FloatCol(default=0)


class Grant(SQLObject):
   class sqlmeta:
      table = 'grants'
      lazyUpdate = True

   user = ForeignKey('User')
   expiration = EnumCol(enumValues=['none', 'time', 'volume', 'drinks'], default='volume')
   status = EnumCol(enumValues=['active', 'expired', 'deleted'], default='active')
   policy = ForeignKey('Policy')
   exp_volume = IntCol(default=0)
   exp_time = IntCol(default=0)
   exp_drinks = IntCol(default=0)
   total_volume = IntCol(default=0)
   total_drinks = IntCol(default=0)

   def AvailableVolume(self):
      """
      return how much volume is available with this grant, at this instant.
      """
      if self.IsExpired():
         return 0
      if self.expiration == 'volume':
         return max(0, self.exp_volume - self.total_volume)
      else:
         return sys.maxint

   def IsExpired(self, extravolume = 0):
      if self.status != 'active':
         return True
      if self.expiration == "none":
         return False
      elif self.expiration == "time":
         return self.exp_time < time.time()
      elif self.expiration == "volume":
         return (extravolume + self.total_volume) >= self.exp_volume
      else:
         return True

   def IncVolume(self, volume):
      self.total_volume += volume
      if self.expiration == 'volume':
         if self.total_volume >= self.exp_volume:
            self.status = 'expired'
      self.syncUpdate()

   def ExpiresBefore(self,other):
      """
      determine if this grant will expire sooner than the given one.

      intuitively, this should return 'true' if this grant should be used
      BEFORE the other one (ie, it expires sooner)
      """
      if self.expiration == 'time':
         if other.expiration == 'time':
            return self.exp_time < other.exp_time
         elif other.expiration == 'none':
            return True
      elif self.expiration == 'none':
         return False

      # fall-thru, XXX
      return False


class User(SQLObject):
   class sqlmeta:
      table = 'users'
      lazyUpdate = True

   username = StringCol(length=32, notNone=True)
   email = StringCol(default='')
   im_aim = StringCol(default='')
   admin = EnumCol(enumValues = ['yes','no'])
   password = StringCol(default='')
   gender = EnumCol(enumValues = ['male','female'])
   weight = FloatCol(default=180.0)
   image_url = StringCol(default='')


class Policy(SQLObject):
   class sqlmeta:
      table = 'policies'
      lazyUpdate = True

   type = EnumCol(enumValues = ['fixed-cost','free'], notNone=True)
   unitcost = FloatCol(default=0.0)
   unitvolume = IntCol(default=0)
   description = StringCol(default='')

   def Cost(self, volume):
      if self.type == 'free':
         return 0.0
      elif self.type == 'fixed-cost':
         return self.unitcost / self.unitvolume * volume


class Token(SQLObject):
   class sqlmeta:
      table = 'tokens'
      lazyUpdate = True

   user = ForeignKey('User', notNone=True)
   keyinfo = StringCol(notNone=True)
   created = DateTimeCol()


class BAC(SQLObject):
   class sqlmeta:
      table = 'bacs'
      lazyUpdate = True

   user = ForeignKey('User')
   drink = ForeignKey('Drink')
   rectime = IntCol(notNone=True)
   bac = FloatCol(notNone=True)

   def ProcessDrink(cls, d):
      """ Store a BAC value given a recent drink """
      prev_bac = 0.0

      matches = BAC.select('user_id=%i' % d.user.id, orderBy='-rectime')
      if matches.count():
         last_bac = matches[0]
         prev_bac = util.decomposeBAC(last_bac.bac, d.endtime - last_bac.rectime)

      now = util.instantBAC(d.user.gender, d.user.weight, d.keg.alccontent,
            units.to_ounces(d.volume))
      # TODO(mikey): fix this factor
      #now = util.decomposeBAC(now, units.to_ounces(d.volume)/12.0*(30*60))

      b = BAC(user=d.user, drink=d.id, rectime=d.endtime, bac=now+prev_bac)
      d.syncUpdate()
   ProcessDrink = classmethod(ProcessDrink)


class GrantCharge(SQLObject):
   class sqlmeta:
      table = 'grantcharges'
      lazyUpdate = True

   grant = ForeignKey('Grant')
   drink = ForeignKey('Drink')
   user = ForeignKey('User')
   volume = IntCol(default=0)


class Binge(SQLObject):
   class sqlmeta:
      table = 'binges'
      lazyUpdate = True

   user = ForeignKey('User', notNone=True)
   startdrink = ForeignKey('Drink')
   enddrink = ForeignKey('Drink')
   volume = IntCol(default=0, notNone=True)
   starttime = IntCol(notNone=True)
   endtime = IntCol(notNone=True)

   def Assign(cls, d):
      """ Create or update a binge given a recent drink """
      binges = list(Binge.select("user_id=%i"%d.user.id,
         orderBy="-id", limit=1))

      # flush binge fetched if it is too old
      if len(binges) != 0:
         if binges[0].endtime < (d.endtime - (60*90)): # XXX fix constant
            binges = []

      # now find or create the current binge, and update it
      if len(binges) == 0:
         last_binge = Binge(user=d.user, startdrink=d,
               enddrink=d, volume=d.volume, starttime=d.endtime,
               endtime=d.endtime)
         last_binge.syncUpdate()
      else:
         last_binge = binges[0]
         last_binge.volume += d.volume
         last_binge.enddrink = d
         last_binge.endtime = d.endtime
         last_binge.syncUpdate()
      return last_binge.id
   Assign = classmethod(Assign)


class Userpic(SQLObject):
   class sqlmeta:
      table = 'userpics'
      lazyUpdate = True

   user = ForeignKey('User', notNone=True)
   filetype = EnumCol(enumValues=['png','jpeg'], default='png', notNone=True)
   modified = DateTimeCol(default=datetime.now)
   data = BLOBCol(length=2**24)

