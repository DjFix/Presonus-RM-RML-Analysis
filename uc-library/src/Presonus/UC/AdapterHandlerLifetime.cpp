#include "core/portable/coresingleton.h"
#include "presonus/uc/adapter_handler.hpp"

namespace Presonus::UC {
// Intentional owning source model. No native private-field layout is asserted.
struct AdapterHandler::OwnedState {
  presonus::uc::CclAdapterServices services;
  presonus::uc::AdapterHandlerState state{services};
  OwnedState() {
    // Native +0x28 binding is documented by the independent process oracle.
    state.refreshIntervalBits = 100;
  }
};

AdapterHandler::AdapterHandler()
    : owned_(std::make_unique<OwnedState>()), state_(owned_->state) {}
AdapterHandler::AdapterHandler(presonus::uc::AdapterSourcePortTag,
                               presonus::uc::AdapterHandlerState &state)
    : state_(state) {}
AdapterHandler::~AdapterHandler() = default;
} // namespace Presonus::UC

DEFINE_STATIC_SINGLETON(Presonus::UC::AdapterHandler)

namespace presonus::uc {
Presonus::UC::AdapterHandler &sourceAdapterSingleton() {
  return Core::Portable::StaticSingleton<
      Presonus::UC::AdapterHandler>::instance();
}
} // namespace presonus::uc
