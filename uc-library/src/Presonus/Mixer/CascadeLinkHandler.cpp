#include "presonus/mixer/CascadeLinkHandler.hpp"
#include "core/system/coredebug.h"
namespace Presonus::Mixer {
void CascadeLinkHandler::connectDevice() {
  Core::DebugPrintf("CascadeLinkHandler::connect to client id=%d\n",
                    clientDiagnosticId_ ? *clientDiagnosticId_ : 0);
  for (int index = 0; index < primary_.count(); ++index)
    pending_.add(primary_.at(index));
}
} // namespace Presonus::Mixer
