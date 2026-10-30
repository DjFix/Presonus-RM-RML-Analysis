#include "presonus/dice/programmer.hpp"

#include <cassert>

namespace Presonus::DICE {
Dice3Programmer::Dice3Programmer(UC::IFirmwareUpdateListener *listener,
                                 const unsigned char *image,
                                 unsigned int length)
    : state_{-1, image, length, listener} {}

Dice3Programmer::~Dice3Programmer() {}

int Dice3Programmer::verify() { return 0; }

void Dice3Programmer::printProgress(const char *text, float value, bool) {
  if (state_.listener) {
    assert(progress_ != nullptr);
    progress_->report(state_.listener, text, value);
  }
}
} // namespace Presonus::DICE
