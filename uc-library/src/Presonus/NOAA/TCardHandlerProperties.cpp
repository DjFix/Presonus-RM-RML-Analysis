#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/router.hpp"
#include "presonus/noaa/status_property.hpp"
#include <stdexcept>
DEFINE_SINGLETON(Presonus::NOAA::TCardHandler)
namespace Presonus::NOAA {
void TCardHandler::setPropertyDeferred(const Core::Property &property) {
  // Exact native literal IDs; payloads are explicit identity-bound projections.
  if (property.type == 1936225136) {
    sendGEQBulkProperty(property);
  } else if (property.type == 1399157877) {
    if (!state_.deferredRate || state_.deferredRate->property != &property ||
        property.size != 40)
      throw std::invalid_argument(
          "NOAA Handler requires size40 rate projection");
    const auto &rate = *state_.deferredRate;
    const int code = rate.value08 < 45000.0f   ? 0
                     : rate.value08 < 49000.0f ? 1
                     : rate.value08 < 90000.0f ? 2
                                               : 3;
    state_.card.sendSampleRate(code, rate.link1c);
  } else if (property.type == 1634038640) {
    if (!state_.router || !state_.deferredRoutes ||
        state_.deferredRoutes->property != &property)
      throw std::invalid_argument(
          "NOAA Handler requires live route projection");
    auto &router = *state_.router;
    const auto &routes = *state_.deferredRoutes;
    router.initRoutes();
    auto destination = routes.word08;
    auto single = [&](std::int32_t count, unsigned char source) {
      for (std::int32_t i = 0; i < count; ++i) {
        router.setAVS48Route(static_cast<unsigned char>(destination), source, 4,
                             0);
        ++destination;
        ++source;
      }
    };
    single(routes.count10, 42);
    single(routes.count18, 56);
    auto paired = [&](std::int32_t count, unsigned char left,
                      unsigned char right) {
      for (std::int32_t i = 0; i < count; ++i) {
        router.setAVS48Route(static_cast<unsigned char>(destination), left, 4,
                             0);
        router.setAVS48Route(static_cast<unsigned char>(destination + 1u),
                             right, 4, 0);
        destination += 2u;
      }
    };
    paired(routes.count1c, 60, 61);
    paired(routes.count20, 58, 58);
  }
}
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
