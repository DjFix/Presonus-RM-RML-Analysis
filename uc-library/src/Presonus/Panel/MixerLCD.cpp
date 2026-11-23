#include "presonus/panel/MixerLCD.hpp"
#include "core/public/corestringbuffer.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include <cstring>
#include <stdexcept>
namespace Presonus::Panel {
void MixerLCD::setAltKeyParam(Core::Portable::Parameter *parameter) {
  altKeyParameter_ = parameter;
}
void MixerLCD::previous() const { state_.book.command(0x2c); }
void MixerLCD::next() const { state_.book.command(0x28); }
void MixerLCD::up() const { state_.book.command(0x20); }
void MixerLCD::down() const { state_.book.command(0x24); }
void MixerLCD::store() const { state_.book.command(0x38); }

void MixerLCD::bindLookupProviders(FrontPanelComponent &frontPanel,
                                   Mixer::MixerComponentBase &mixer) {
  if (!mixer.childLookupParameters)
    throw std::invalid_argument("MixerLCD mixer lookup root is missing");
  frontLookup_ = &frontPanel.portableState().component;
  mixerLookup_ = mixer.childLookupParameters;
}

Core::Portable::Parameter *
MixerLCD::lookupElementParameter(const char *name) const {
  if (!mixerLookup_)
    throw std::logic_error("MixerLCD lookup providers are not bound");

  const Core::CString128 boundedName{name};
  const char *const text = boundedName.str();
  const char *const prefix = frontLookup_->getName();
  if (std::strstr(text, prefix) != text)
    return mixerLookup_->lookupParameter(name);

  // A match at the start skips one byte after the prefix, even when that
  // byte is not a slash. Exact matches and an empty suffix pass an empty path.
  const auto suffixOffset = std::strlen(prefix) + 1;
  return frontLookup_->lookupParameter(
      suffixOffset < std::strlen(text) ? text + suffixOffset : "");
}
} // namespace Presonus::Panel
