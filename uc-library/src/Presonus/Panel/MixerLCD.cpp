#include "presonus/panel/MixerLCD.hpp"
namespace Presonus::Panel {
void MixerLCD::previous() const { state_.book.command(0x2c); }
void MixerLCD::next() const { state_.book.command(0x28); }
void MixerLCD::up() const { state_.book.command(0x20); }
void MixerLCD::down() const { state_.book.command(0x24); }
void MixerLCD::store() const { state_.book.command(0x38); }
} // namespace Presonus::Panel
