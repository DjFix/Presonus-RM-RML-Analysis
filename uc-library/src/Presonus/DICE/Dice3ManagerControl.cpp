#include "presonus/dice/manager.hpp"
#include "presonus/dice/sysex.hpp"
#include <stdexcept>
namespace Presonus::DICE {
std::int32_t Dice3Manager::resetDice3() {
  if (!portableSubsystem_)
    throw std::logic_error("Dice3Manager subsystem is required");
  portableSubsystem_->resetDice3();
  portableSubsystem_->markPortableInfoPending();
  DiceInfo ignored;
  return getDice3Info(&ignored);
}
std::int32_t Dice3Manager::setDice3Serial(int serial, unsigned char unit) {
  if (!portableSubsystem_)
    throw std::logic_error("Dice3Manager subsystem is required");
  return portableSubsystem_->programSerialData(
      static_cast<unsigned int>(serial), unit);
}
} // namespace Presonus::DICE
