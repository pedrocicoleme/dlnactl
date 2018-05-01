import time
import datetime
import logging
from functools import partial

import upnpclient
import lxml.etree


logger = logging.getLogger('dlnactl')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s %(name)s-%(lineno)s %(levelname)s %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


AVTRANSPORT_SERVICE_ID = "urn:upnp-org:serviceId:AVTransport"
INSTANCE_ID = 0
SPEED = "1"
CHANNEL_MASTER = "Master"



service_original = upnpclient.upnp.Service

class Service(service_original):
    def _read_state_vars(self):
        for statevar_node in self._findall('serviceStateTable/stateVariable'):
            findtext = partial(statevar_node.findtext, namespaces=statevar_node.nsmap)
            findall = partial(statevar_node.findall, namespaces=statevar_node.nsmap)
            name = findtext('name')
            datatype = findtext('dataType')
            send_events = statevar_node.attrib.get('sendEvents', 'yes').lower() == 'yes'
            allowed_values = set([e.text for e in findall('allowedValueList/allowedValue')])

            allowed_value_range = {
                e.tag.split('}')[-1]: (
                    int(e.text) if isinstance(e.text, str) and datatype.startswith('ui')
                    else e.text)
                for c in findall('allowedValueRange')
                for e in c.getchildren()}

            self.statevars[name] = dict(
                name=name,
                datatype=datatype,
                allowed_values=allowed_values,
                allowed_value_range=allowed_value_range,
                send_events=send_events
            )

print("monkey-patching")
upnpclient.upnp.Service = Service


class NotImplemented(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


def raise_(exception):
    raise exception()


def secs_from_time_str(time_str):
    timebsecs = time.strptime(time_str, "%H:%M:%S")

    return datetime.timedelta(
        hours=tdur.tm_hour, minutes=tdur.tm_min, seconds=tdur.tm_sec).total_seconds()


def seek_abs(device, desired_target):
    """
    Go to a specified absolute position on the track
    """
    media_info = device.AVTransport.GetPositionInfo(InstanceID=0)

    track_duration_t = secs_from_time_str(media_info["TrackDuration"])

    track_desired_t = secs_from_time_str(desired_target)

    target = min(track_duration_t, desired_target_t)

    m, s = divmod(target, 60)
    h, m = divmod(m, 60)

    return device.AVTransport.Seek(
        InstanceID=INSTANCE_ID, Unit="ABS_TIME", Target="{}:{02d}:{02d}".format(h, m, s))


def seek_percent(device, desired_percent):
    """
    Go to the % in time of the current track
    """
    media_info = device.AVTransport.GetPositionInfo(InstanceID=0)

    track_duration_t = secs_from_time_str(media_info["TrackDuration"])

    return seek_abs(device, track_duration_t * max(0, min(1, desired_percent / 100.0)))


def seek_track(device, desired_track):
    """
    Go to the specified track of the media
    """
    media_info = device.AVTransport.GetMediaInfo(InstanceID=0)

    nr_tracks = media_info["NrTracks"]

    target = max(1, min(nr_tracks, desired_track))

    return device.AVTransport.Seek(
        InstanceID=INSTANCE_ID, Unit="TRACK_NR", Target=target)


def seek_track_rel(device, desired_step=1):
    """
    Go to a track relative to the current one
    """
    position_info = device.AVTransport.GetPositionInfo(InstanceID=0)

    current_track = position_info["Track"]

    desired_track = current_track + desired_step

    return seek_track(device, desired_track)


def get_volume(device):
    """
    Return the volume normalized from 0 to 100%
    """
    max_volume = device.RenderingControl.statevars["Volume"]["allowed_value_range"]["maximum"]

    current_volume = device.RenderingControl.GetVolume(
        InstanceID=INSTANCE_ID, Channel=CHANNEL_MASTER)["CurrentVolume"]

    return int(current_volume * 100 / max_volume)


def set_volume(device, desired_volume):
    """
    Set the volume from 0 to 100%
    """
    max_volume = device.RenderingControl.statevars["Volume"]["allowed_value_range"]["maximum"]

    desired_volume_clipped = max(0, min(100, desired_volume))

    return device.RenderingControl.SetVolume(
        InstanceID=INSTANCE_ID, Channel=CHANNEL_MASTER, DesiredVolume=int((
            max_volume * desired_volume) / 100))


def set_media(device, media_uri):
    pass


AVAILABLE_COMMANDS = {
    "play": lambda device: device.AVTransport.Play(InstanceID=INSTANCE_ID, Speed=SPEED),
    "pause": lambda device: device.AVTransport.Pause(InstanceID=INSTANCE_ID),
    "stop": lambda device: device.AVTransport.Stop(InstanceID=INSTANCE_ID),
    "seek_abs": seek_abs,
    "seek_percent": seek_percent,
    "seek_track": seek_track,
    "next_track": lambda device: seek_track_rel(device, 1),
    "previous_track": lambda device: seek_track_rel(device, -1),
    "next_media": lambda device: raise_(NotImplemented),
    "previous_media": lambda device: raise_(NotImplemented),
    "set_media": lambda device: raise_(NotImplemented),
    "set_next_media": lambda device: raise_(NotImplemented),
    "get_state": lambda device: device.AVTransport.GetTransportInfo(
        InstanceID=INSTANCE_ID)["CurrentTransportState"],
    "get_media_info": lambda device: device.AVTransport.GetMediaInfo(
        InstanceID=INSTANCE_ID),
    "get_position_info": lambda device: device.AVTransport.GetPositionInfo(
        InstanceID=INSTANCE_ID),
    "set_mute": lambda device, mute: device.RenderingControl.SetMute(
        InstanceID=INSTANCE_ID, Channel=CHANNEL_MASTER, DesiredMute=mute),
    "set_volume": set_volume,
    "get_mute": lambda device: device.RenderingControl.GetMute(
        InstanceID=INSTANCE_ID, Channel=CHANNEL_MASTER)["CurrentMute"],
    "get_volume": get_volume}


def available_devices():
    """
    List all devices that are AVTransport media renderers
    """
    devices = []

    for device in upnpclient.discover():
        for service in device.services:
            if service.service_id == AVTRANSPORT_SERVICE_ID:
                logger.info(service.actions)

                devices.append(device)

    return devices


if __name__ == "__main__":
    for device in available_devices():
        logger.info(device.friendly_name)

        logger.info(device.AVTransport.Play.argsdef_in)

        # continue

        AVAILABLE_COMMANDS["set_volume"](device, 20)

        AVAILABLE_COMMANDS["play"](device)

        time.sleep(5)
        AVAILABLE_COMMANDS["pause"](device)

        time.sleep(5)
        AVAILABLE_COMMANDS["play"](device)

        AVAILABLE_COMMANDS["seek_abs"](device, "0:01:30")
