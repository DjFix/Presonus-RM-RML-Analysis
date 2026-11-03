#include "presonus/mixer/PermissionsComponent.hpp"
#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "presonus/trial08/MixerComponentBase.hpp"

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
void PermissionsComponent::resetPermissionsPW() {
  bindings_.accessCodeParameters->getParameterByTag(4)->resetValue(false);
  saveAccessCode();
}
void PermissionsComponent::getAccessCodeFileName(
    Core::Portable::FileName &filename) const {
  filename = bindings_.mixer->getDataDir("permissions");
  filename.descend("access");
  filename.append(".code");
}
void PermissionsComponent::saveAccessCode() const {
  auto *parameter = bindings_.accessCodeParameters->getParameterByTag(4);
  if (!parameter)
    return;
  auto *code = Core::Portable::StringParam::cast(parameter);
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  attributes.set(parameter->getName(), code->getText().str());
  Core::Portable::FileName filename;
  getAccessCodeFileName(filename);
  Core::Portable::ArchiveUtils::saveInBackground(filename.str(), attributes);
}
} // namespace Presonus::Mixer
