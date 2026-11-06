#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/coreproperty.h"
#include "core/system/corethread.h"
#include "presonus/noaa/card_handler_state.hpp"
#include "presonus/noaa/sysex_receiver.hpp"
#include <memory>
namespace Presonus::NOAA {
// Original RTTI establishes these four public bases. Modern source Thread
// replaces unavailable legacy CoreThread; native offsets/ARM ABI are unclaimed.
// Portable source ownership and modern CCL layout; no original ARM ABI claim.
// Default construction owns real Card/Router/CCL state. Bind required live
// HAL, resources and property projections before publishing requests. The
// original ordinary return declarations and legacy exception ABI are
// unresolved.
class TCardHandler : public Core::IPropertyHandler,
                     public Core::Threads::Thread,
                     public Core::Portable::Singleton<TCardHandler>,
                     public SysexReceiver {
public:
  TCardHandler();
  TCardHandler(presonus::noaa::CardHandlerSetupTag,
               presonus::noaa::CardHandlerState &state,
               presonus::dice::ResponseServices &response);
  ~TCardHandler() override;
  void setProperty(const Core::Property &) override;
  // Independent binding access; callers serialize and retain projected values.
  presonus::noaa::CardHandlerState &portableHandlerState() { return state_; }
  // Requires a successfully started thread; join before destroying borrowed
  // state. Source-port void override, not an independently recovered return
  // type.
  void release() override;
  // Source-port int override; native unencoded return declaration unresolved.
  // Calls across Handler instances sharing the static idle deadline must be
  // serialized by the caller. Borrowed state/queue must outlive the thread.
  int threadEntry() override;
  void getProperty(Core::Property &) override;
  bool accepts(const SysexPacket &) override;
  // Portable void contract; original ordinary return declaration unresolved.
  void purgeEvents();
  // Provisional source-port void return; original return declaration
  // unresolved.
  void setPropertyDeferred(const Core::Property &);
  unsigned long long getAlternateMac();
  unsigned int sendGEQBulkProperty(const Core::Property &);

private:
  struct Owned;
  std::unique_ptr<Owned> owned_;
  bool registered_ = false;
  bool started_ = false;
  presonus::noaa::CardHandlerState &state_;
};
} // namespace Presonus::NOAA
