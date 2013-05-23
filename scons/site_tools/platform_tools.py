#!/usr/bin/env python
# 
# Copyright (c) 2013, Roboterclub Aachen e.V.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Roboterclub Aachen e.V. nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY ROBOTERCLUB AACHEN E.V. ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL ROBOTERCLUB AACHEN E.V. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
# 
# DESCRIPTION
# 
# This tool checks which files are needed for a specific target
# using the xml device file and adds a custom builder for all template files
# and for other files that need to be copied to the generated folder
#
# WARNING: Do NOT name this file platform.py because this overrides a
#          different platform module used by /usr/lib/scons/SCons/Tool/tex.py


from SCons.Script import *
import os

from configfile import Scanner # for header and source file endings

# add device_file module from tools to path
# this is apparently not pythonic, but I see no other way to do this
# without polluting the site_tools directory or haveing duplicate code
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'device_files'))
from device import DeviceFile
from driver import DriverFile
from parser_exception import ParserException

#------------------------------------------------------------------------------
# Builder that finds the xml device file
# expects the content of env['XPCC_DEVICE'] as source
# use some dummy target like '#device-file'
def platform_tools_find_xml_device_file_action(target, source, env):
	device = str(source[0])
	xml_path = os.path.join(env['XPCC_PLATFORM_PATH'], 'xml')
	files = []
	device_file = None
	while device != None and len(device) > 0:
		device_file = os.path.join(xml_path, device + '.xml')
		files.append(device_file)
		if os.path.isfile(device_file):
			break
		else:
			device = device[:-1]
			device_file = None
	# Check for error
	if device_file == None:
		emsg = "XPCC Error: Could not find xml device file." + os.linesep
		for f in files:
			emsg += "Tried: " + f + os.linesep
		raise SCons.Errors.BuildError(node=target, errstr=emsg)
	# Now we need to parse the Xml File
	next_target = env.ParseXmlDeviceFile('#parsed-device-file', File(device_file))
	env.Depends(next_target, target) # next target depends on this target
	return None

def platform_tools_find_xml_device_file_emitter(target, source, env):
	# Stub that might be used in the future
	return target, source

def platform_tools_find_xml_device_file_string(target, source, env):
	return "Searching Xml Device File for: '%s'" % (str(source[0]))
#------------------------------------------------------------------------------
# Builder that reads the content of a xml device file
# expects the xml device file name as source
# use some dummy target like '#parsed-device-file'
def platform_tools_parse_xml_device_file_action(target, source, env):
	dev = DeviceFile(str(source[0]))
	# Todo: Do something with the properties...
	print "Properties: %s" % dev.getProperties(env['XPCC_DEVICE'])
	# Add Drivers to Build Tree
	drivers = dev.getDriverList(env['XPCC_DEVICE'], env['XPCC_PLATFORM_PATH'])
	for d in drivers:
		target = '#driver-' + d['type'] + '-' + d['name']
		if d['driver_file'] == None: # if there is no xml file we need a fake source
			source = Value(target + "-source")
		else:
			source = File(os.path.join(env['XPCC_PLATFORM_PATH'], d['driver_file']))
		print "target=%s, source=%s" % (target, source)
		next_target = env.ParseXmlDriverFile(target, source, driver=d)
		env.Depends(next_target, target) # next target depends on this target
	return None

def platform_tools_parse_xml_device_file_emitter(target, source, env):
	# Stub that might be used in the future
	return target, source

def platform_tools_parse_xml_device_file_string(target, source, env):
	return "Parsing Xml Device File: '%s'" % (os.path.basename(str(source[0])))

#------------------------------------------------------------------------------
# Builder that reads the content of a xml driver property file
# Use the xml driver file as a target or some dummy target if
# it does not exist. The target only matters as a dependency,
# because if the driver xml is changed, different files
# may need to be built
# Also add driver=DriverDictionary when calling the builder
# driver dictionary need to be built by calling Driver.toDict
def platform_tools_parse_xml_driver_file_action(target, source, env):
	if not env.has_key('driver'):
		raise SCons.Errors.UserError, "Use 'ParseXmlDriverFile(..., driver = ...)'"
	d = DriverFile.fromDict(env['driver'])
	build = d.getBuildList(env['XPCC_PLATFORM_PATH'])
	for f in build:
		src = os.path.join(env['XPCC_PLATFORM_PATH'], f[0])
		tar = os.path.join(env['XPCC_GENERATED_PATH'], f[1])
		if len(f) == 3:
			res = env.Jinja2Template(target = tar, source = src, substitutions = f[2])
		else:
			res = env.Install(tar, src) # copy f[0] to f[1]
		# check if target is header file
		if os.path.splitext(tar)[1] in Scanner.HEADER:
			env.AppendUnique(CPPPATH = os.path.dirname(f[1]))
		# or source file
		elif os.path.splitext(tar)[1] in Scanner.SOURCE:
			# Very ugly and probably does not work.....
			if env['XPCC_PLATFORM_SOURCES'] == None:
				env['XPCC_PLATFORM_SOURCES'] = []
			env['XPCC_PLATFORM_SOURCES'].append(tar)

def platform_tools_parse_xml_driver_file_emitter(target, source, env):
	Depends(target, SCons.Node.Python.Value(env['driver']))
	return target, source

def platform_tools_parse_xml_driver_file_string(target, source, env):
	return "Parsing Xml Driver File: '%s'" % (os.path.basename(str(source[0])))





# -----------------------------------------------------------------------------
def generate(env, **kw):
	# Set some paths used by this file
	env['XPCC_PLATFORM_PATH'] = os.path.join(env['XPCC_LIBRARY_PATH'], 'xpcc', 'architecture', 'platform')
	env['XPCC_GENERATED_PATH'] = os.path.join(env['XPCC_LIBRARY_PATH'], 'xpcc', 'architecture', 'generated_platform_' + env['XPCC_DEVICE'])

	# Add Custom builders etc.
	env['BUILDERS']['FindXmlDeviceFile'] = \
		SCons.Script.Builder(
			action = env.Action(platform_tools_find_xml_device_file_action, platform_tools_find_xml_device_file_string),
			emitter = platform_tools_find_xml_device_file_emitter)
	env['BUILDERS']['ParseXmlDeviceFile'] = \
		SCons.Script.Builder(
			action = env.Action(platform_tools_parse_xml_device_file_action, platform_tools_parse_xml_device_file_string),
			emitter = platform_tools_parse_xml_device_file_emitter)
	env['BUILDERS']['ParseXmlDriverFile'] = \
		SCons.Script.Builder(
			action = env.Action(platform_tools_parse_xml_driver_file_action, platform_tools_parse_xml_driver_file_string),
			emitter = platform_tools_parse_xml_driver_file_emitter)

	# Dummy Env Variables
	env['XPCC_PLATFORM_SOME_DUMMY_DICT'] = {'name': 'what ever', 'stubstitutions': {'a': 1, 'b': 2}}

	# Specify how to build the platform dir
	env.FindXmlDeviceFile('#device-file', SCons.Node.Python.Value(env['XPCC_DEVICE'])) # first dummy target
	env.AlwaysBuild(env.Alias('p_test', '#device-file'))
	

# -----------------------------------------------------------------------------
def exists(env):
	return True
