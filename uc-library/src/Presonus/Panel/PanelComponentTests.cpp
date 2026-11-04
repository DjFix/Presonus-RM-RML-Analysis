#include "core/system/coredebug.h"
#include "presonus/panel/PanelComponent.hpp"
namespace Presonus::Panel {
int PanelComponent::runTests(int, int, char **) {
  Core::DebugPrintf(
      "A class that inherits PanelComponent didn't implement runTests(...)\n");
  return 0;
}
} // namespace Presonus::Panel
