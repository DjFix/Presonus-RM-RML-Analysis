#include "presonus/noaa/card.hpp"
#include "presonus/noaa/status_property.hpp"
namespace Presonus::NOAA {
void TCard::getStatusProperty(NOAAStatusProperty &property) {
  property.setWord(0x08, state_.observedWord14);
  property.setWord(0x0c, state_.observedWord20);
  property.setWord(0x10, state_.observedWord24);
  property.setWord(0x14, state_.observedWord28);
  property.setByte(0x26, state_.observedWord18 != 0);
  property.setByte(0x27, state_.observedWord1c != 0);
  property.setByte(0x28, isMounted());
  property.setByte(0x24, isFirmwareCompatible(2));
  property.setByte(0x25, isFirmwareCompatible(3));
  property.setByte(0x29, state_.observedWord40 != 0);
  property.setWord(0x18, state_.observedWord34);
  property.setWord(0x1c, state_.observedWord38);
  property.setWord(0x20, state_.observedWord3c);
  property.setByte(0x2a, state_.observedByte48);
  property.setWord(0x2c, state_.observedWord4c);
  property.setWord(0x30, state_.observedWord50);
  property.setWord(0x34, state_.observedWord54);
  property.setWord(0x38, state_.observedWord58);
}
} // namespace Presonus::NOAA
