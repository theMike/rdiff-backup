# Copyright 2002 Ben Escoto
#
# This file is part of rdiff-backup.
#
# rdiff-backup is free software; you can redistribute it and/or modify
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# rdiff-backup is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with rdiff-backup; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

"""list, delete, and otherwise manage increments"""

from __future__ import generators
from log import Log
import Globals, Time, static, manage


class ManageException(Exception): pass

def get_file_type(rp):
	"""Returns one of "regular", "directory", "missing", or "special"."""
	if not rp.lstat(): return "missing"
	elif rp.isdir(): return "directory"
	elif rp.isreg(): return "regular"
	else: return "special"

def get_inc_type(inc):
	"""Return file type increment represents"""
	assert inc.isincfile()
	type = inc.getinctype()
	if type == "dir": return "directory"
	elif type == "diff": return "regular"
	elif type == "missing": return "missing"
	elif type == "snapshot": return get_file_type(inc)
	else: assert None, "Unknown type %s" % (type,)

def describe_incs_parsable(incs, mirror_time, mirrorrp):
	"""Return a string parsable by computer describing the increments

	Each line is a time in seconds of the increment, and then the
	type of the file.  It will be sorted oldest to newest.  For example:

	10000 regular
	20000 directory
	30000 special
	40000 missing
	50000 regular    <- last will be the current mirror

	"""
	incpairs = [(Time.stringtotime(inc.getinctime()), inc) for inc in incs]
	incpairs.sort()
	result = ["%s %s" % (time, get_inc_type(inc)) for time, inc in incpairs]
	result.append("%s %s" % (mirror_time, get_file_type(mirrorrp)))
	return "\n".join(result)

def describe_incs_human(incs, mirror_time, mirrorrp):
	"""Return a string describing all the the root increments"""
	incpairs = [(Time.stringtotime(inc.getinctime()), inc) for inc in incs]
	incpairs.sort()

	result = ["Found %d increments:" % len(incpairs)]
	for time, inc in incpairs:
		result.append("    %s   %s" %
					  (inc.dirsplit()[1], Time.timetopretty(time)))
	result.append("Current mirror: %s" % Time.timetopretty(mirror_time))
	return "\n".join(result)

def delete_earlier_than(baserp, time):
	"""Deleting increments older than time in directory baserp

	time is in seconds.  It will then delete any empty directories
	in the tree.  To process the entire backup area, the
	rdiff-backup-data directory should be the root of the tree.

	"""
	baserp.conn.manage.delete_earlier_than_local(baserp, time)

def delete_earlier_than_local(baserp, time):
	"""Like delete_earlier_than, but run on local connection for speed"""
	assert baserp.conn is Globals.local_connection
	def yield_files(rp):
		yield rp
		if rp.isdir():
			for filename in rp.listdir():
				for sub_rp in yield_files(rp.append(filename)):
					yield sub_rp

	for rp in yield_files(baserp):
		if ((rp.isincfile() and
			 Time.stringtotime(rp.getinctime()) < time) or
			(rp.isdir() and not rp.listdir())):
			Log("Deleting increment file %s" % rp.path, 5)
			rp.delete()


class IncObj:
	"""Increment object - represent a completed increment"""
	def __init__(self, incrp):
		"""IncObj initializer

		incrp is an RPath of a path like increments.TIMESTR.dir
		standing for the root of the increment.

		"""
		if not incrp.isincfile():
			raise ManageException("%s is not an inc file" % incrp.path)
		self.incrp = incrp
		self.time = Time.stringtotime(incrp.getinctime())

	def getbaserp(self):
		"""Return rp of the incrp without extensions"""
		return self.incrp.getincbase()

	def pretty_time(self):
		"""Return a formatted version of inc's time"""
		return Time.timetopretty(self.time)

	def full_description(self):
		"""Return string describing increment"""
		s = ["Increment file %s" % self.incrp.path,
			 "Date: %s" % self.pretty_time()]
		return "\n".join(s)
