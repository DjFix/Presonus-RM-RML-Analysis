#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <optional>
namespace Core {
struct Property;
}
namespace Presonus::NOAA {
class TCard;
class TCardRouter;
struct NOAASetupProperty;
struct NOAAStatusProperty;
} // namespace Presonus::NOAA
namespace Presonus::UC {
class IFirmwareUpdateListener;
}
namespace presonus::noaa {
class CardHandlerEventQueue;
// Explicit values for native reads at +8..24. Identity binds a live property;
// this is not its representation or an original declaration.
struct ImmediatePropertyProjection {
  const Core::Property *property;
  std::array<std::uint32_t, 5> words{};
};
// Explicit projections of native payload reads. Names identify observed
// offsets, not recovered original field declarations or native object layout.
// Explicit serialized application payload, independent from host Property
// layout. The owner supplies exactly semanticBytes-8 observed payload bytes.
struct CardHandlerPayloadProjection {
  const Core::Property *property;
  std::array<unsigned char, 504> bytes{};
  unsigned count = 0;
};
struct DeferredRouteProjection {
  const Core::Property *property;
  std::uint32_t word08;
  std::int32_t count10, count18, count1c, count20;
};
struct DeferredRateProjection {
  const Core::Property *property;
  float value08;
  std::int32_t link1c;
};
// Independent borrowed bindings; no original Handler layout/ownership claim.
// Caller serializes access and keeps every bound object alive through calls.
struct CardHandlerState {
  Presonus::NOAA::TCard &card;
  // Explicit numeric projection of original Card word2c; never an opaque cast.
  std::optional<std::uint32_t> expectedSerial;
  // Required only for the matching dispatch path. Identity must match the
  // incoming Core::Property base; never reinterpret an arbitrary property.
  Presonus::NOAA::NOAAStatusProperty *statusProperty = nullptr;
  const Core::Property *geqProperty = nullptr;
  // Original bytes at offsets8..40, independent of native Property layout.
  const std::array<unsigned char, 33> *geqPayload = nullptr;
  // Borrowed source-port count; producer release-stores and consumer
  // acquire-loads. Not a claim about original +0xa4 type, ordering or native
  // object layout.
  std::atomic<std::uint32_t> *pendingEventCount = nullptr;
  Presonus::NOAA::TCardRouter *router = nullptr;
  const DeferredRouteProjection *deferredRoutes = nullptr;
  const DeferredRateProjection *deferredRate = nullptr;
  // Independent stop publication, corresponding only to observed native byte
  // +0x64. A source-port threadEntry consumes this with acquire ordering.
  // Not an original field declaration, native layout or ordering claim.
  std::atomic<bool> stopRequested{false};
  // Independent optional FIFO; bind before thread start and join before unbind.
  CardHandlerEventQueue *eventQueue = nullptr;
  const ImmediatePropertyProjection *immediate = nullptr;
  const CardHandlerPayloadProjection *payload = nullptr;
  const Presonus::NOAA::NOAASetupProperty *setup = nullptr;
  const Core::Property *scriptProperty = nullptr;
  const char *script = nullptr;
  // A typed pointer is bound independently from the observed native integer.
  const Core::Property *updateProperty = nullptr;
  Presonus::UC::IFirmwareUpdateListener *updateListener = nullptr;
  int updateMode = 0;
  // Observed native constructor writes only; meanings/declarations unresolved.
  // These independent numeric projections do not establish native fields/ABI.
  unsigned char observedByte65 = 0, observedByte66 = 0;
};
struct CardHandlerSetupTag {};
inline constexpr CardHandlerSetupTag cardHandlerSetupTag{};
} // namespace presonus::noaa
