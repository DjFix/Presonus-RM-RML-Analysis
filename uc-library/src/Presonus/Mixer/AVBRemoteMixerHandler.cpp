#include "presonus/mixer/AVBRemoteMixerHandler.hpp"
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
