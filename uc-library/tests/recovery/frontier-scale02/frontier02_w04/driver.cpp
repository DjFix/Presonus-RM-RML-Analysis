#include "presonus/panel/SPIControlGroup.hpp"
#include "presonus/panel/control.hpp"
#include <cstdarg>
#include <cstdlib>
#include <iostream>
#include <linux/spi/spidev.h>
#include <vector>

static int calls = 0;
static int observedFd = 0;
static unsigned long observedRequest = 0;
static std::vector<unsigned> observedTx;
extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  va_list ap;
  va_start(ap, request);
  auto *message = va_arg(ap, spi_ioc_transfer *);
  va_end(ap);
  ++calls;
  observedFd = fd;
  observedRequest = request;
  auto *tx = reinterpret_cast<const unsigned char *>(message->tx_buf);
  auto *rx = reinterpret_cast<unsigned char *>(message->rx_buf);
  observedTx.assign(tx, tx + message->len);
  for (unsigned i = 0; i < message->len; ++i)
    rx[i] = static_cast<unsigned char>(0xa0 + i);
  return -1;
}
int main() {
  int groupId, argument, width;
  while (std::cin >> groupId >> argument >> width) {
    calls = 0;
    Presonus::Panel::SPIControlGroup group(groupId, argument, width);
    std::cout << presonus::panel_binding::ControlGroupAccess::groupId(group)
              << ' ' << group.count() << ' ' << group.payloadByteCount() << ' '
              << group.transportDescriptor() << ' ' << group.isDirty() << ' '
              << calls << '\n';
    // Default descriptor prevents I/O and preserves the constructor's dirty
    // bit.
    group.onIdle();
    if (!group.isDirty() || calls != 0 ||
        !presonus::panel_binding::ControlGroupAccess::ownsState(group))
      std::abort();
  }
  // Source integration: actual ControlGroup controls feed the same idle path.
  Presonus::Panel::Control a(3), b(4), c(5);
  presonus::panel::ControlAccess::lastLevel(a) = 1;
  presonus::panel::ControlAccess::lastLevel(b) = 0;
  presonus::panel::ControlAccess::lastLevel(c) = -1;
  Presonus::Panel::SPIControlGroup group(1, 0, 2);
  group.add(&a);
  group.add(&b);
  group.add(&c);
  presonus::spi_port::LinuxTransfer transfer;
  group.attachTransport(7, transfer);
  calls = 0;
  group.onIdle();
  std::cout << calls << ' ' << observedFd << ' ' << observedRequest << ' '
            << group.isDirty() << ' ' << unsigned(group.transmitted()[0]) << ' '
            << unsigned(group.transmitted()[1]) << ' '
            << unsigned(group.received()[0]) << ' '
            << unsigned(group.received()[1]) << '\n';
  group.onIdle();
  if (calls != 1)
    std::abort();
  std::uint32_t words[] = {1, 0, 0xffffffffu};
  Core::ConstVector<std::uint32_t> borrowed(words, 3);
  Presonus::Panel::SPIControlGroup independent(borrowed, 2, 7, transfer);
  if (independent.isDirty())
    std::abort();
  independent.markDirty(true);
  calls = 0;
  independent.onIdle();
  if (calls != 1 || observedTx != std::vector<unsigned>({5, 0}))
    std::abort();
}
