#include "presonus/reconstruction200/large02_w04.hpp"
#include "core/system/coredebug.h"
#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <stdexcept>
namespace {
void dispatch(std::vector<presonus::mixer::RemoteMixerConnector *> &entries,
              Presonus::MixerClientComponentBase *component) {
  const auto count = entries.size();
  for (std::size_t i = 0; i < count; ++i) {
    // Native captures an initial loop bound but reloads the current vector.
    // The source port rejects mutation that would select native fallback/null.
    if (i >= entries.size() || !entries[i])
      throw std::logic_error("remote mixer connector unavailable");
    entries[i]->setComponent(component);
  }
}
} // namespace
namespace Presonus::Mixer {
AVBRemoteMixerHandler::AVBRemoteMixerHandler(
    presonus::mixer::RemoteMixerState &s)
    : state_(s) {}
AVBRemoteMixerHandler::~AVBRemoteMixerHandler() {
  if (state_.activation)
    state_.activation->removeObserver(this);
}
void AVBRemoteMixerHandler::activate() {
  MixerClientComponentBase *component = nullptr;
  if (state_.activation && state_.activation->getValue() > 0.f) {
    component = state_.component;
    if (!component) {
      Core::DebugPrintf(
          "  AVB remote mixer went away... turning stagebox OFF\n");
      if (state_.activation)
        state_.activation->setValue(0.f, false);
    }
  }
  dispatch(state_.activators, component);
}
void AVBRemoteMixerHandler::onRestoredSelection() {
  if (state_.savedSelection && state_.activation)
    state_.activation->setValue(state_.savedSelection->getValue(), false);
}
void AVBRemoteMixerHandler::paramChanged(Core::Portable::Parameter *p,
                                         int msg) {
  if (msg == 3) {
    if (p == state_.activation)
      activate();
  } else if (msg == 5) {
    p->removeObserver(this);
    if (p == state_.activation)
      state_.activation = nullptr;
  }
}
void AVBRemoteMixerHandler::setMixerComponent(MixerClientComponentBase *c) {
  state_.component = c;
  connect();
}
void AVBRemoteMixerHandler::connect() {
  dispatch(state_.connectors, state_.component);
  activate();
}
} // namespace Presonus::Mixer

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
