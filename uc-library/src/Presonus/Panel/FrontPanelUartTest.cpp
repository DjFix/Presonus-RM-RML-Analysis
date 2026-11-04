#include "core/system/coredebug.h"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/uart_comm.hpp"
#include <cstring>
// Original local global-C++ identity. Preserve a separately emitted callable
// body. The first-byte synchronization loop intentionally has no aggregate
// deadline; getNextChar has a per-call timeout. This preserves the observed
// native loop.
__attribute__((noinline, used)) static void dspUartTest() {
  char probe[] = "PreSonus StudioLive AI";
  char received[32] = {};
  Presonus::Panel::UARTComm first, second;
  Core::DebugPrintf(" *********  DSP UART Test Begins ******** \n");
  first.open("/dev/ttyS0");
  second.open("/dev/ttyS1");
  second.write(probe, static_cast<int>(std::strlen(probe)));
  Core::DebugPrintf("ttyS1 sent:  %s\n", probe);
  Core::DebugPrintf("ttyS0 received: ");
  for (std::size_t i = 0; i < std::strlen(probe);) {
    received[i] = static_cast<char>(first.getNextChar(1));
    if (received[0] != 'P')
      continue;
    Core::DebugPrintf("%c", received[i]);
    ++i;
  }
  Core::DebugPrintf("\n");
  if (std::strcmp(probe, received) != 0) {
    Core::DebugPrintf("DSP UART Test FAILED - ***** Message sent from ttyS1 to "
                      "ttyS0 don't match!!!!! *****\n");
  } else {
    first.write(probe, static_cast<int>(std::strlen(probe)));
    Core::DebugPrintf("ttyS0 sent:  %s\n", probe);
    Core::DebugPrintf("ttyS1 received: ");
    for (std::size_t i = 0; i < std::strlen(probe);) {
      received[i] = static_cast<char>(second.getNextChar(1));
      if (received[0] != 'P')
        continue;
      Core::DebugPrintf("%c", received[i]);
      ++i;
    }
    Core::DebugPrintf("\n");
    if (std::strcmp(probe, received) == 0)
      Core::DebugPrintf("***** DSP UART Test PASSED!!!!! *****\n");
    else
      Core::DebugPrintf("DSP UART Test FAILED - ***** Message sent from ttyS0 "
                        "to ttyS1 don't match!!!!! *****\n");
  }
  Core::DebugPrintf(" *********  DSP UART Test Complete ******** \n");
  first.close();
  second.close();
}
void Presonus::Panel::FrontPanelComponent::uartTest() { dspUartTest(); }
