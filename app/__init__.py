from app.assist import HotelAssistant
from app.room_moves import change_room
from app.room_status import set_room_status, mark_room_out_of_order, mark_room_out_of_service, restore_room
from app.room_inventory import set_showroom, inventory_by_type, room_is_sellable
from app.availability import is_room_available, get_available_rooms

HotelAssistant.change_room = change_room
HotelAssistant.set_room_status = set_room_status
HotelAssistant.mark_room_out_of_order = mark_room_out_of_order
HotelAssistant.mark_room_out_of_service = mark_room_out_of_service
HotelAssistant.restore_room = restore_room
HotelAssistant.set_showroom = set_showroom
HotelAssistant.inventory_by_type = inventory_by_type
HotelAssistant.room_is_sellable = room_is_sellable
HotelAssistant.is_room_available = is_room_available
HotelAssistant.get_available_rooms = get_available_rooms
