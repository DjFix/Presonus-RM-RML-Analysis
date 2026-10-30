#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/status_property.hpp"
#include <stdexcept>
DEFINE_SINGLETON(Presonus::NOAA::TCardHandler)
namespace Presonus::NOAA {
bool TCardHandler::accepts(const SysexPacket &packet) {
  return packet.length > 1 && packet.bytes[1] == 29;
}
void TCardHandler::getProperty(Core::Property &property) {
  if (property.type != NOAAStatusProperty::kID)
    return;
  if (!state_.statusProperty ||
      static_cast<Core::Property *>(state_.statusProperty) != &property)
    throw std::invalid_argument("NOAA Handler requires live status projection");
  state_.card.getStatusProperty(*state_.statusProperty);
}
unsigned long long TCardHandler::getAlternateMac() {
  if (!state_.expectedSerial)
    throw std::invalid_argument("NOAA Handler requires serial projection");
  return (10ull << 32) |
         (state_.card.generateAlternateMac(*state_.expectedSerial) |
          0x92000000u);
}
unsigned int TCardHandler::sendGEQBulkProperty(const Core::Property &property) {
  if (state_.geqProperty != &property || !state_.geqPayload)
    throw std::invalid_argument("NOAA Handler requires live GEQ projection");
  unsigned char bytes[36];
  bytes[0] = 240;
  bytes[1] = 29;
  for (unsigned i = 0; i < 33; ++i)
    bytes[i + 2] = (*state_.geqPayload)[i] & 127;
  bytes[35] = 247;
  SysexPacket packet(bytes, 36);
  post(packet);
  waitAck(500);
  return 0;
}
} // namespace Presonus::NOAA
