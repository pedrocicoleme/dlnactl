import time
import datetime

import upnpclient


AVTRANSPORT_SERVICE_ID = "urn:upnp-org:serviceId:AVTransport"


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
        InstanceID=0, Unit="ABS_TIME", Target="{}:{02d}:{02d}".format(h, m, s))


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
        InstanceID=0, Unit="TRACK_NR", Target=target)


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
    max_volume = device.statevars["Volume"]

    current_volume = device.RenderingControl.GetVolume(
        InstanceID=0, Channel="Master")["CurrentVolume"]

    return current_volume * 100.0 / max_volume


def set_volume(device, desired_volume):
    """
    Set the volume from 0 to 100%
    """
    max_volume = device.statevars["Volume"]

    desired_volume_clipped = max(0, min(100, desired_volume))

    return device.RenderingControl.SetVolume(
        InstanceID=0, Channel="Master", DesiredVolume=(
            max_volume * desired_volume) / 100.0)


AVAILABLE_COMMANDS = {
    "play": lambda device: device.AVTransport.Play(InstanceID=0, Speed="1"),
    "pause": lambda device: device.AVTransport.Pause(InstanceID=0),
    "stop": lambda device: device.AVTransport.Stop(InstanceID=0),
    "seek_abs": seek_abs,
    "seek_track": seek_track,
    "next_track": lambda device: seek_track_rel(device, 1),
    "previous_track": lambda device: seek_track_rel(device, -1),
    "next_media": lambda device: raise_(NotImplemented),
    "previous_media": lambda device: raise_(NotImplemented),
    "set_media": lambda device: raise_(NotImplemented),
    "set_next_media": lambda device: raise_(NotImplemented),
    "get_state": lambda device: device.AVTransport.GetTransportInfo(
        InstanceID=0)["CurrentTransportState"],
    "get_media_info": lambda device: device.AVTransport.GetMediaInfo(
        InstanceID=0),
    "get_position_info": lambda device: device.AVTransport.GetPositionInfo(
        InstanceID=0),
    "set_mute": lambda device, mute: device.RenderingControl.SetMute(
        InstanceID=0, Channel="Master", DesiredMute=mute),
    "set_volume": set_volume,
    "get_mute": lambda device: device.RenderingControl.GetMute(
        InstanceID=0, Channel="Master")["CurrentMute"],
    "get_volume": get_volume}


def available_devices():
    """
    List all devices that are AVTransport media renderers
    """
    devices = []

    for device in upnpclient.discover():
        for service in device.services:
            if service.service_id == AVTRANSPORT_SERVICE_ID:
                print(service.actions)

                devices.append(device)

    return devices


if __name__ == "__main__":
    for device in available_devices():
        print(device.friendly_name)

        print(device.AVTransport.Play.argsdef_in)

        AVAILABLE_COMMANDS["play"](device)

        import time
        time.sleep(5)
        AVAILABLE_COMMANDS["pause"](device)

        time.sleep(5)
        AVAILABLE_COMMANDS["play"](device)

        AVAILABLE_COMMANDS["seek_abs"](device, "0:01:30")
