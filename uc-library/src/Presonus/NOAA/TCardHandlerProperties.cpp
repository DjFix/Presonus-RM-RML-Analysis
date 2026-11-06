#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/card_handler_events.hpp"
#include "presonus/noaa/router.hpp"
#include "presonus/noaa/status_property.hpp"
#include <stdexcept>
DEFINE_SINGLETON(Presonus::NOAA::TCardHandler)
namespace Presonus::NOAA {
void TCardHandler::setProperty(const Core::Property &property) {
  auto queue = [&]() -> presonus::noaa::CardHandlerEventQueue & {
    if (!state_.eventQueue)
      throw std::invalid_argument("Handler requires event queue");
    return *state_.eventQueue;
  };
  auto router = [&]() -> TCardRouter & {
    if (!state_.router)
      throw std::invalid_argument("Handler requires Router");
    return *state_.router;
  };
  if (property.type == 0x73657475) {
    if (!state_.setup ||
        static_cast<const Core::Property *>(state_.setup) != &property)
      throw std::invalid_argument("Handler requires live setup property");
    Core::Threads::ScopedLock lock(queue().mainLock());
    router().open(*state_.setup);
    state_.card.open(*state_.setup);
    state_.card.start(false);
    Core::Threads::Thread::start();
    started_ = true;
    return;
  }
  if (property.type == 0x73657269 || property.type == 0x65666972 ||
      property.type == 0x666c6576) {
    Core::Threads::ScopedLock lock(queue().mainLock());
    purgeEvents();
    if (property.type == 0x73657269)
      state_.card.programSerialReset();
    if (property.type == 0x65666972)
      state_.card.eraseFirmware();
    return;
  }
  if (property.type == 0x75647461) {
    if (property.size < 16 || state_.updateProperty != &property)
      throw std::invalid_argument("Handler requires typed update projection");
    purgeEvents();
    Core::Threads::ScopedLock lock(queue().mainLock());
    state_.card.updateFirmware(state_.updateListener, state_.updateMode);
    return;
  }
  if (property.type == 0x73637270) {
    if (property.size < 9 || state_.scriptProperty != &property ||
        !state_.script)
      throw std::invalid_argument("Handler requires live script projection");
    purgeEvents();
    Core::Threads::ScopedLock lock(queue().mainLock());
    router().routeScript(state_.script);
    return;
  }
  // Immediate dispatch reads a typed projection. Values retain native word and
  // low-byte semantics without assuming a modern Property payload layout.
  const int minimum = [&] {
    switch (property.type) {
    case 0x67716677:
      return 10;
    case 0x3274726b:
      return 13;
    case 0x636c6b70:
      return 12;
    case 0x6d6d7574:
    case 0x73706466:
      return 16;
    case 0x64727470:
    case 0x73626d72:
    case 0x74706472:
    case 0x74626176:
      return 17;
    case 0x67657274:
    case 0x726f7574:
      return 20;
    case 0x61767372:
    case 0x61736672:
      return 21;
    case 0x64746174:
    case 0x69707464:
    case 0x61646272:
      return 25;
    default:
      return 24;
    }
  }();
  auto immediate =
      [&]() -> const presonus::noaa::ImmediatePropertyProjection & {
    if (property.size < minimum || !state_.immediate ||
        state_.immediate->property != &property)
      throw std::invalid_argument("Handler requires live immediate projection");
    return *state_.immediate;
  };
  auto w = [&](unsigned i) { return static_cast<int>(immediate().words[i]); };
  auto b = [&](unsigned i) {
    return static_cast<unsigned char>(immediate().words[i]);
  };
  auto mode = [&] { return state_.card.portableCardState().observedWord14; };
  switch (property.type) {
  case 0x67716677:
    router().setGEQToFWRoute(
        b(0), static_cast<unsigned char>(immediate().words[0] >> 8));
    return;
  case 0x63726f74:
    router().setMixerCustomInputRoute(b(0), b(1), w(2), w(3));
    return;
  case 0x64727470:
    router().setAvbTapeRxToDigitalReturnRoute(w(0), w(1), b(2) != 0);
    return;
  case 0x64746174:
    if (mode() == 1)
      router().setDspToAvbTxRoute(w(0), w(1), w(2), w(3), b(4) != 0);
    return;
  case 0x64746e70:
    if (mode() == 2)
      router().setDspToDanteTxRoute(w(0), w(1), w(2), w(3));
    else if (mode() == 1)
      router().setDspToAvbTxRoute(w(0), w(1), w(2), w(3), false);
    return;
  case 0x6c626172:
    router().setLinkBusToAvbRoute(w(0), w(1), w(2), w(3));
    return;
  case 0x73626d72:
    router().setAvbStageBoxMainRoute(w(0), w(1), b(2));
    return;
  case 0x6d6d7574:
    router().setMixerMuteInputRoute(b(0), w(1));
    return;
  case 0x616c6272:
    router().setAvbToLinkBusRoute(w(0), w(1), w(2), w(3));
    return;
  case 0x61767372:
    router().setAVS48Route(b(0), b(1), w(2), b(3));
    return;
  case 0x636c6b70:
    state_.card.setClockSource(w(0));
    return;
  case 0x61736672:
    router().setAvbToSlaveFwRecordRoute(w(0), w(1), w(2), b(3) != 0);
    return;
  case 0x67657274:
    router().setGEQTDMSlotInsert(immediate().words[0], immediate().words[1],
                                 immediate().words[2]);
    return;
  case 0x74706472:
    router().setAvbTapeLRToAvbTxRoute(w(0), w(1), b(2));
    return;
  case 0x74626176:
    router().setTalkbackToAvbTxRoute(w(0), w(1), b(2));
    return;
  case 0x69707464:
    router().setInputToDanteTxRoute(w(0), w(1), w(2), w(3), b(4));
    return;
  case 0x69746176:
    router().setInputToAvbTxRoute(w(0), w(1), w(3), w(2));
    return;
  case 0x3274726b:
    router().set2TrackInputRoute(b(0), b(1));
    return;
  case 0x61646272:
    router().setAvbToDacBypassRoute(w(0), w(1), w(2), w(3), b(4) != 0);
    return;
  case 0x73706466:
    router().setSPDIFRoute(
        b(0), static_cast<unsigned char>(immediate().words[0] >> 8), w(1));
    return;
  case 0x726f7574:
    if (w(2) == 0) {
      Core::Threads::ScopedLock lock(queue().mainLock());
      router().setMixerInputRoute(b(0), w(1), false);
    } else
      router().setMixerInputRoute(b(0), w(1), true);
    return;
  default:
    break;
  }
  // Source-port fail-closed sizes replace native out-of-pool/null dereferences.
  if (property.size < 8 || property.size > 512)
    throw std::invalid_argument("Handler semantic size must be 8..512");
  presonus::noaa::CardHandlerEvent event(property, property.size);
  if (state_.payload && state_.payload->property == &property) {
    if (state_.payload->count != static_cast<unsigned>(property.size - 8))
      throw std::invalid_argument("Handler payload size binding mismatch");
    event.payload = *state_.payload;
  } else if (property.size > 8 &&
             !(state_.deferredRate &&
               state_.deferredRate->property == &property) &&
             !(state_.deferredRoutes &&
               state_.deferredRoutes->property == &property) &&
             !(state_.geqProperty == &property && state_.geqPayload)) {
    throw std::invalid_argument(
        "Handler requires value-owned payload projection");
  }
  if (state_.immediate && state_.immediate->property == &property)
    event.immediate = *state_.immediate;
  if (state_.deferredRate && state_.deferredRate->property == &property)
    event.rate = *state_.deferredRate;
  if (state_.deferredRoutes && state_.deferredRoutes->property == &property)
    event.routes = *state_.deferredRoutes;
  if (state_.geqProperty == &property && state_.geqPayload)
    event.geq = *state_.geqPayload;
  while (!queue().enqueue(event)) {
    if (state_.stopRequested.load(std::memory_order_acquire))
      return;
    Core::Threads::CurrentThread::sleep(4);
  }
}
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
