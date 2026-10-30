#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/coreproperty.h"
#include "core/system/corethread.h"
#include "presonus/noaa/card_handler_state.hpp"
#include "presonus/noaa/sysex_receiver.hpp"
namespace Presonus::NOAA {
// Original RTTI establishes these four public bases. Modern source Thread
// replaces unavailable legacy CoreThread; native offsets/ARM ABI are unclaimed.
// Unknown original functional slots remain pure. No original lifecycle claim.
class TCardHandler : public Core::IPropertyHandler,
                     public Core::Threads::Thread,
                     public Core::Portable::Singleton<TCardHandler>,
                     public SysexReceiver {
public:
  TCardHandler(presonus::noaa::CardHandlerSetupTag,
               presonus::noaa::CardHandlerState &state,
               presonus::dice::ResponseServices &response)
      : Core::Threads::Thread("NOAA Handler source port"), state_(state) {
    setPortableResponseServices(response);
  }
  ~TCardHandler() override = default;
  void setProperty(const Core::Property &) override = 0;
  void release() override = 0;
  int threadEntry() override = 0;
  void getProperty(Core::Property &) override;
  bool accepts(const SysexPacket &) override;
  unsigned long long getAlternateMac();
  unsigned int sendGEQBulkProperty(const Core::Property &);

private:
  presonus::noaa::CardHandlerState &state_;
};
} // namespace Presonus::NOAA
