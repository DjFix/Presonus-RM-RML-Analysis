#include "presonus/panel/uart_comm.hpp"

extern "C" __attribute__((noinline)) void
dice_secondary_destroy(Presonus::Panel::UARTComm *port) {
  port->~UARTComm();
}

extern "C" __attribute__((noinline)) void
dice_secondary_delete(Presonus::Panel::UARTComm *port) {
  delete port;
}
