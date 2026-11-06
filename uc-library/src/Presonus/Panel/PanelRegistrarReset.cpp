#include "core/system/coredebug.h"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/surface_panel/InputPin.hpp"
#include "presonus/surface_panel/OutputPin.hpp"

// Original internal-linkage global scope retained. GPIO classes own their
// actual source-port lifecycles; no callback replaces pin construction/cleanup.
static void resetCS(int first, int second, bool bootloader) {
  Core::DebugPrintf(" FPR: resetCS %d %d %d\n", first, second, bootloader);
  Presonus::Panel::OutputPin reset(first);
  reset.set(0);
  Core::Threads::CurrentThread::sleep(20);
  if (bootloader) {
    Presonus::Panel::OutputPin boot(second);
    reset.set(1);
    Core::Threads::CurrentThread::sleep(20);
    Core::DebugPrintf(" FPR: CS to Bootloader Mode\n");
  } else {
    Presonus::Panel::InputPin boot(second, nullptr);
    reset.set(0);
    Core::Threads::CurrentThread::sleep(20);
    reset.set(1);
    Core::DebugPrintf(" FPR: CS to normal mode\n");
  }
}
namespace Presonus::Panel {
void PanelRegistrar::resetBoard(int mode, int board) {
  Core::Threads::ScopedLock lock(resetLock_);
  Core::DebugPrintf(" FPR: resetBoard section:%d  isbootloader:%d\n", mode,
                    board);
  switch (mode) {
  case 0:
    resetCS(103, 108, board != 0);
    break;
  case 1:
    resetCS(102, 110, board != 0);
    break;
  case 2: {
    OutputPin reset(32);
    OutputPin boot(139);
    OutputPin select(21);
    Core::DebugPrintf(" FPR: TCard reset.  Bootloader:%d\n", board != 0);
    reset.set(0);
    Core::Threads::CurrentThread::sleep(20);
    select.set(board != 0 ? 1 : 0);
    Core::Threads::CurrentThread::sleep(20);
    boot.set(board != 0 ? 0 : 1);
    Core::Threads::CurrentThread::sleep(20);
    reset.set(1);
    break;
  }
  default:
    break;
  }
}
} // namespace Presonus::Panel
