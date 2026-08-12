from app.assist import HotelAssistant
from app.room_moves import change_room
from app.room_status import set_room_status, mark_room_out_of_order, mark_room_out_of_service, restore_room

HotelAssistant.change_room = change_room
HotelAssistant.set_room_status = set_room_status
HotelAssistant.mark_room_out_of_order = mark_room_out_of_order
HotelAssistant.mark_room_out_of_service = mark_room_out_of_service
HotelAssistant.restore_room = restore_room
