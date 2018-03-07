import upnpclient


fn = None


AVTRANSPORT_SERVICE_ID = "urn:upnp-org:serviceId:AVTransport"


class NotImplemented(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


def raise_(exception):
    raise exception()


AVAILABLE_COMMANDS = {
    "play": lambda device: device.AVTransport.Play(InstanceID=0, Speed="1"),
    "pause": lambda device: device.AVTransport.Pause(InstanceID=0),
    "stop": lambda device: device.AVTransport.Stop(InstanceID=0),
    "seek": lambda device, target: device.AVTransport.Seek(
        InstanceID=0, Unit="ABS_TIME", Target=target),
    "next_track": fn,
    "previous_track": fn,
    "next_media": lambda device: raise_(NotImplemented),
    "previous_media": lambda device: raise_(NotImplemented),
    "set_media": fn,
    "set_next_media": lambda device: raise_(NotImplemented),
    "get_state": lambda device: device.AVTransport.GetTransportInfo(
        InstanceID=0)["CurrentTransportState"],
    "get_media_info": lambda device: device.AVTransport.GetMediaInfo(
        InstanceID=0),
    "get_track_info": lambda device: device.AVTransport.GetPositionInfo(
        InstanceID=0),
    "set_mute": lambda device, mute: device.RenderingControl.SetMute(
        InstanceID=0, Channel="Master", DesiredMute=mute),
    "set_volume": lambda device, volume: device.RenderingControl.SetMute(
        InstanceID=0, Channel="Master", DesiredVolume=volume),
    "get_mute": lambda device: device.RenderingControl.GetMute(
        InstanceID=0, Channel="Master"),
    "get_volume": lambda device: device.RenderingControl.GetVolume(
        InstanceID=0, Channel="Master")}


def available_devices():
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
        time.sleep(10)
        AVAILABLE_COMMANDS["pause"](device)

        time.sleep(5)
        AVAILABLE_COMMANDS["play"](device)

        # AVAILABLE_COMMANDS["seek"](device, "0:01:30")
