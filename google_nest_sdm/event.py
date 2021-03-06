"""Events from pubsub subscriber."""

from abc import abstractmethod, ABC
import datetime

from .auth import AbstractAuth
from .traits import BuildTraits, Command
from .registry import Registry

EVENT_ID = "eventId"
EVENT_SESSION_ID = "eventSessionId"
TIMESTAMP = "timestamp"
RESOURCE_UPDATE = "resourceUpdate"
NAME = "name"
TRAITS = "traits"
EVENTS = "events"
RELATION_UPDATE = "relationUpdate"
TYPE = "type"
SUBJECT = "subject"
OBJECT = "object"

EVENT_MAP = Registry()


class EventBase(ABC):
    """Base class for all event types."""

    def __init__(self, data):
        """Initialize EventBase."""
        self._data = data

    @property
    def event_id(self) -> str:
        """A unique event identifier."""
        return self._data[EVENT_ID]

    @property
    def event_session_id(self) -> str:
        """Used to authenticate follow up request related to this event."""
        return self._data[EVENT_SESSION_ID]


@EVENT_MAP.register()
class CameraMotionEvent(EventBase):
    """Motion has been detected by the camera."""
    NAME = "sdm.devices.events.CameraMotion.Motion"


@EVENT_MAP.register()
class CameraPersonEvent(EventBase):
    """A person has been detected by the camera."""
    NAME = "sdm.devices.events.CameraPerson.Person"


@EVENT_MAP.register()
class CameraSoundEvent(EventBase):
    """Sound has been detected by the camera."""
    NAME = "sdm.devices.events.CameraSound.Sound"


@EVENT_MAP.register()
class DoorbellChimeEvent(EventBase):
    """The doorbell has been pressed."""
    NAME = "sdm.devices.events.DoorbellChime.Chime"


class RelationUpdate:
    """Represents a relational update for a resource."""

    def __init__(self, raw_data: dict):
        self._raw_data = raw_data

    @property
    def type(self) -> str:
        """The type of relation event 'CREATED', 'UPDATED', 'DELETED'."""
        return self._raw_data[TYPE]

    @property
    def subject(self) -> str:
        """The resource that the object is now in relation with."""
        return self._raw_data[SUBJECT]

    @property
    def object(self) -> str:
        """The resource that triggered the event."""
        return self._raw_data[OBJECT]


def BuildEvents(events: dict, event_map: dict) -> dict:
    """Builds a trait map out of a response dict."""
    result = {}
    for (event, event_data) in events.items():
        if not event in event_map:
            continue
        cls = event_map[event]
        result[event] = cls(event_data)
    return result


class EventMessage:
    """Event for a change in trait value or device action."""

    def __init__(self, raw_data: dict, auth: AbstractAuth):
        """Initialize an EventMessage."""
        self._raw_data = raw_data
        self._auth = auth

    @property
    def event_id(self) -> str:
        """A unique event identifier."""
        return self._raw_data[EVENT_ID]

    @property
    def timestamp(self) -> datetime.datetime:
        """Time when the event was published."""
        event_timestamp = self._raw_data[TIMESTAMP]
        return datetime.datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))

    @property
    def resource_update_name(self) -> str:
        """Returns the id of the device that was updated."""
        if not RESOURCE_UPDATE in self._raw_data:
            return None
        return self._raw_data[RESOURCE_UPDATE][NAME]

    @property
    def resource_update_events(self) -> dict:
        """Returns the set of events that happened."""
        if not RESOURCE_UPDATE in self._raw_data:
            return None
        events = self._raw_data[RESOURCE_UPDATE].get(EVENTS, {})
        return BuildEvents(events, EVENT_MAP)

    @property
    def resource_update_traits(self) -> dict:
        """Returns the set of traits that were updated."""
        if not RESOURCE_UPDATE in self._raw_data:
            return None
        cmd = Command(self.resource_update_name, self._auth)
        events = self._raw_data[RESOURCE_UPDATE].get(TRAITS, {})
        return BuildTraits(events, cmd)

    @property
    def relation_update(self) -> RelationUpdate:
        """Represent a relational update for a resource."""
        if not RELATION_UPDATE in self._raw_data:
            return None
        return RelationUpdate(self._raw_data[RELATION_UPDATE])


class EventCallback(ABC):
    """For implementers to get notified about EventMessages."""

    @abstractmethod
    def handle_event(self, event_message: EventMessage):
        """Process an incoming EventMessage."""
