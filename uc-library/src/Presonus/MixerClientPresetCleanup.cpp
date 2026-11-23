#include "presonus/mixer_state/MixerState.hpp"
#include <new>

namespace Presonus {
void MixerClientComponentBase::clearPresets(
    Core::Vector<IPresetHandler::Preset *> &ownedRecords) {
  const int count = ownedRecords.count();
  for (int index = 0; index < count; ++index)
    ::operator delete(ownedRecords.at(index));
  ownedRecords.resize(0);
}
} // namespace Presonus
