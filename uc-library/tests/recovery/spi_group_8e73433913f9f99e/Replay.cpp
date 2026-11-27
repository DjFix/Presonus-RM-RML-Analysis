#include "presonus/panel/SPIControl.hpp"
#include "presonus/panel/SPIControlGroup.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <linux/spi/spidev.h>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using Presonus::Panel::SPIControlGroup;
namespace {
std::vector<std::string> events;
int openResult = -1;
void *deletingGroup = nullptr;
void *deletingChild = nullptr;
int childFrees = 0;
int groupFrees = 0;
int sizedChildFrees = 0;
int sizedGroupFrees = 0;
bool observeDeletes = false;
int childDeletes = 0;
void require(bool value) {
  if (!value)
    std::abort();
}
std::string bytes(const std::uint8_t *p, int n) {
  std::ostringstream s;
  s << '[';
  for (int i = 0; i < n; ++i) {
    if (i)
      s << ',';
    s << unsigned(p[i]);
  }
  s << ']';
  return s.str();
}
struct Child : Presonus::Panel::Control {
  Child() : Control(7) {}
  ~Child() override {
    ++childDeletes;
    if (observeDeletes)
      events.push_back("[\"control_delete\",32768]");
  }
};
} // namespace
extern "C" int __wrap_open(const char *path, int flags, ...) {
  require(std::strcmp(path, "/offline/spi") == 0);
  events.push_back("[\"open\",\"/offline/spi\"," + std::to_string(flags) + "]");
  return openResult;
}
extern "C" int __wrap_close(int) { std::abort(); }
extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  va_list ap;
  va_start(ap, request);
  auto *m = va_arg(ap, spi_ioc_transfer *);
  va_end(ap);
  require(m->len >= 2 && m->len <= 5);
  require(m->speed_hz == 0 && m->delay_usecs == 0 && m->bits_per_word == 0 &&
          m->cs_change == 0);
  require(m->tx_nbits == 0 && m->rx_nbits == 0 && m->word_delay_usecs == 0 &&
          m->pad == 0);
  auto *tx = reinterpret_cast<const std::uint8_t *>(m->tx_buf);
  auto *rx = reinterpret_cast<std::uint8_t *>(m->rx_buf);
  events.push_back("[\"ioctl\"," + std::to_string(fd) + "," +
                   std::to_string(request) + "," + std::to_string(m->len) +
                   "," + bytes(tx, m->len) + ",[0,0,0,0,0]]");
  for (unsigned i = 0; i < m->len; ++i) {
    require(rx[i] == 0);
    rx[i] = 0x70 + i;
  }
  return -7;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
namespace {
void observeFree(void *p, bool sized, std::size_t size) {
  if (p == deletingGroup) {
    require(++groupFrees == 1);
    if (sized) {
      require(size == sizeof(SPIControlGroup));
      ++sizedGroupFrees;
    }
    if (observeDeletes) {
      observeDeletes = false;
      events.push_back("[\"delete\",0]");
    }
  }
  if (p == deletingChild) {
    require(++childFrees == 1);
    if (sized) {
      require(size == sizeof(Child));
      ++sizedChildFrees;
    }
  }
}
} // namespace
extern "C" void __wrap__ZdlPv(void *p) {
  observeFree(p, false, 0);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  observeFree(p, true, size);
  __real__ZdlPvm(p, size);
}
int main(int argc, char **argv) {
  require(argc == 11);
  std::string mode = argv[1];
  int n = std::stoi(argv[2]);
  int fd = std::stoi(argv[3]);
  int dirty = std::stoi(argv[4]);
  int enabled = std::stoi(argv[5]);
  int count = std::stoi(argv[6]);
  long long value = std::stoll(argv[7]);
  openResult = std::stoi(argv[8]);
  int groupId = std::stoi(argv[9]);
  std::string slots = argv[10];
  SPIControlGroup *g = new SPIControlGroup(groupId, -2, n);
  require(g->transportDescriptor() == -1 && g->isDirty());
  presonus::spi_port::LinuxTransfer transfer;
  g->attachTransport(fd, transfer);
  g->markDirty(dirty);
  Presonus::Panel::IPanelIO *io = g;
  Uart_Msg_Type msg{{0xa5, 0x41, 0x7e, 0xff}};
  auto before = msg;
  std::vector<std::unique_ptr<Presonus::Panel::Control>> idleControls;
  std::unique_ptr<Presonus::Panel::Control> capacityChild;
  int result = 0;
  bool assigned = false;
  if (mode == "ctor") {
    require(g->count() == 0);
    require(presonus::panel_binding::ControlGroupAccess::groupId(*g) ==
            groupId);
    require(presonus::panel_binding::ControlGroupAccess::ownsState(*g));
    g->attachTransport(-1, transfer);
    g->markDirty(true);
  } else if (mode == "bitbang")
    result = g->bitBang(value);
  else if (mode == "open")
    result = io->open("/offline/spi");
  else if (mode == "read")
    result = io->readMsg(msg);
  else if (mode == "write")
    result = io->writeMsg(msg);
  else if (mode == "hispeed")
    result = io->enableHISpeed(enabled);
  else if (mode == "broadcast")
    result = io->broadcast(nullptr);
  else if (mode == "close")
    io->close();
  else if (mode == "sort")
    g->sort();
  else if (mode == "idle") {
    for (int i = 0; i < count; ++i) {
      idleControls.emplace_back(new Presonus::Panel::Control(i));
      presonus::panel::ControlAccess::lastLevel(*idleControls.back()) =
          i % 3 ? 1 : 0;
      g->ControlGroup::add(idleControls.back().get());
    }
    g->onIdle();
  } else if (mode == "add") {
    auto retained = std::make_unique<Presonus::Panel::SPIControl>(7);
    auto *control = retained.get();
    for (int i = 0; i < count; ++i)
      g->ControlGroup::add(nullptr);
    g->add(control);
    if (count < 256)
      retained.release();
    assigned = presonus::panel::ControlAccess::io(*control) == io;
    require(assigned);
    require(g->count() == (count < 256 ? count + 1 : 256));
    g->markDirty(false);
    control->broadcastValue(1);
    require(g->isDirty());
    g->markDirty(dirty);
  } else if (mode == "d0" || mode == "d1") {
    if (slots == "owned") {
      std::unique_ptr<Presonus::Panel::Control> child(new Child);
      deletingChild = child.get();
      g->add(child.release());
      if (count > 1)
        g->ControlGroup::add(nullptr);
    } else {
      for (int i = 0; i < count; ++i)
        g->ControlGroup::add(nullptr);
      if (slots == "full") {
        capacityChild.reset(new Child);
        deletingChild = capacityChild.get();
        g->add(capacityChild.get());
        require(g->count() == 256);
        require(presonus::panel::ControlAccess::io(*capacityChild) == io);
      }
    }
    deletingGroup = g;
    observeDeletes = true;
    if (mode == "d0") {
      delete g;
      g = nullptr;
    } else {
      g->~SPIControlGroup();
      observeDeletes = false;
      require(groupFrees == 0); // D1 itself must not deallocate its receiver.
      __wrap__ZdlPv(g); // Explicit caller cleanup after the D1 observation.
      g = nullptr;
    }
    require(groupFrees == 1);
    require(childDeletes == (slots == "owned" ? 1 : 0));
    require(childFrees == (slots == "owned" ? 1 : 0));
    if (slots == "full") {
      capacityChild.reset();
      require(childDeletes == 1 && childFrees == 1);
    }
  }
  require(msg.bytes == before.bytes);
  std::cout << "{\"deallocation\":{\"group_frees\":" << groupFrees
            << ",\"child_frees\":" << childFrees
            << ",\"sized_group_frees\":" << sizedGroupFrees
            << ",\"sized_child_frees\":" << sizedChildFrees
            << "},\"result\":" << result;
  if (g)
    std::cout << ",\"descriptor\":" << g->transportDescriptor()
              << ",\"dirty\":" << g->isDirty()
              << ",\"tx\":" << bytes(g->transmitted().data(), 5)
              << ",\"rx\":" << bytes(g->received().data(), 5)
              << ",\"count\":" << g->count()
              << ",\"io_assigned\":" << (assigned ? "true" : "false");
  std::cout << ",\"events\":[";
  for (std::size_t i = 0; i < events.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << events[i];
  }
  std::cout << "]}" << std::endl;
  if (g)
    delete g;
}
