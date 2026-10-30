#pragma once
#include <array>
#include <cstdint>
#include <optional>
namespace Core {
struct Property;
}
namespace Presonus::NOAA {
class TCard;
struct NOAAStatusProperty;
} // namespace Presonus::NOAA
namespace presonus::noaa {
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
};
struct CardHandlerSetupTag {};
inline constexpr CardHandlerSetupTag cardHandlerSetupTag{};
} // namespace presonus::noaa
