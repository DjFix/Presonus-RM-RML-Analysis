#include "presonus/mixer/PermissionsComponent.hpp"

namespace Presonus::Mixer {
void PermissionsComponent::getSelectedFileName(
    Core::Portable::FileName &fileName) const {
  if (bindings_.selectedName)
    bindings_.getFileName(bindings_.context, *this, fileName,
                          *bindings_.selectedName);
}

void PermissionsComponent::getMixString(
    Core::CStringBuffer<128> &string) const {
  bindings_.mix->toString(string.getBuffer(), 128);
}

void PermissionsComponent::getOtherString(
    Core::CStringBuffer<128> &string) const {
  bindings_.other->toString(string.getBuffer(), 128);
}

void PermissionsComponent::auxLinkingChanged() {
  bindings_.loadSelectedDevice(bindings_.context, *this);
  bindings_.devicePermissionsChanged(bindings_.ownerContext, *this);
  bindings_.dirty = 1;
}

void PermissionsComponent::setFullPermissions(bool enabled) {
  if (enabled && bindings_.restricted == 0)
    bindings_.mix->fromString("FOH", false);
}
} // namespace Presonus::Mixer
