#include "core/system/coredebug.h"
#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/mixer/AVBRemoteMixerHandler.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <stdexcept>
namespace Presonus::Mixer {
void AVBCascadeManager::onIdle() {
  if (idleTarget_)
    idleTarget_->onIdle();
}
} // namespace Presonus::Mixer

namespace Presonus::Mixer {
const presonus::mixer::CascadeClientBinding &
AVBCascadeManager::binding(void *identity) const {
  for (const auto &entry : clientBindings_)
    if (entry.identity == identity)
      return entry;
  throw std::logic_error("unbound cascade client typed view");
}
void *AVBCascadeManager::getConnectedClient() const {
  return selected_ ? selected_->getComponent() : nullptr;
}
void *AVBCascadeManager::getConnectedClientComponent() const {
  return getConnectedClient();
}
Core::Portable::Parameter *AVBCascadeManager::getSlaveParam(int tag) const {
  void *identity = getConnectedClient();
  if (!identity)
    return nullptr;
  auto *component = binding(identity).component;
  if (!component)
    throw std::logic_error("missing cascade Core component view");
  auto *global = component->findChild("global");
  return global ? global->getParameterByTag(tag) : nullptr;
}
void AVBCascadeManager::sendEvent(UC::Event &event) {
  if (!getConnectedClient())
    return;
  auto *client = binding(getConnectedClient()).client;
  if (!client)
    throw std::logic_error("missing cascade ClientImplementation view");
  client->sendEvent(event);
}
namespace {
void sendMessage(AVBCascadeManager &self,
                 const UC::MessageAttributes &attributes) {
  UC::MutableMessageEvent event(attributes, 0x4a4d, 0);
  // Real non-const owner; no original inheritance/layout is inferred.
  auto &header = const_cast<UC::Event &>(
      presonus::uc::MutableMessageEventPortAccess::event(event).header);
  auto binding = self.sourcePortMessageOrigins().bind(
      presonus::uc::MutableMessageEventPortAccess::event(event));
  if (!binding)
    throw std::logic_error("cascade message origin registration rejected");
  self.sendEvent(header);
}
} // namespace
presonus::uc::ClientTypedOrigins &
AVBCascadeManager::sourcePortMessageOrigins() const {
  if (!messageOrigins_)
    throw std::logic_error("cascade message origin registry is not configured");
  return *messageOrigins_;
}
void AVBCascadeManager::presetStored(const char *component, int slot) {
  if (!selected_)
    return;
  UC::MessageAttributes attributes("StoreCascadeScene");
  attributes.setURL("presets");
  attributes.set("AVBSceneSlot", static_cast<Core::int64>(slot));
  attributes.set("AVBMComponentID", component, false);
  sendMessage(*this, attributes);
}
void AVBCascadeManager::presetRecalled(const char *component, int slot) {
  if (!selected_)
    return;
  UC::MessageAttributes attributes("RecallCascadeScene");
  attributes.setURL("presets");
  attributes.set("AVBSceneSlot", static_cast<Core::int64>(slot));
  attributes.set("AVBMComponentID", component, false);
  sendMessage(*this, attributes);
}
void AVBCascadeManager::muteGroupStored(int index) {
  if (!selected_)
    return;
  UC::MessageAttributes attributes("presetMuteGroup");
  attributes.setURL("mutegroup");
  attributes.set("presetMuteGroupIndex", static_cast<Core::int64>(index));
  sendMessage(*this, attributes);
}
} // namespace Presonus::Mixer
