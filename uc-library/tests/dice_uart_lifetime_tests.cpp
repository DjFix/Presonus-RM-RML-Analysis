#include "presonus/dice/uart_assembly.hpp"
#include <array>
#include <cstdarg>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Presonus::DICE::Dice3Uart;
using presonus::dice::UartLifetimeAccess;
using Presonus::Panel::UARTComm;
extern "C" void dice_c1(void *) asm("_ZN8Presonus4DICE9Dice3UartC1Ev");
extern "C" void dice_c2(void *) asm("_ZN8Presonus4DICE9Dice3UartC2Ev");
extern "C" void dice_d1(void *) asm("_ZN8Presonus4DICE9Dice3UartD1Ev");
extern "C" void dice_d2(void *) asm("_ZN8Presonus4DICE9Dice3UartD2Ev");
extern "C" void dice_d0(void *) asm("_ZN8Presonus4DICE9Dice3UartD0Ev");
extern "C" void dice_secondary_destroy(UARTComm *);
extern "C" void dice_secondary_delete(UARTComm *);

namespace {
std::string activeCase;
void require(bool value) {
  if (!value)
    throw std::runtime_error("lifetime fixture contract: " + activeCase);
}
struct SingletonAccess : Core::Portable::Singleton<Dice3Uart> {
  static void set(Dice3Uart *value) { theInstance = value; }
  static Dice3Uart *get() { return theInstance; }
};
struct Event {
  char kind;
  std::uintptr_t pointer;
  int value = 0;
};
struct Context {
  bool enabled = false, constructing = false;
  Dice3Uart *object = nullptr, *other = nullptr;
  std::uintptr_t uart = 0, dice = 0, buffer = 0, owner = 0, vector = 0;
  bool bufferFreed = false, ownerFreed = false, vectorFreed = false,
       objectFreed = false;
  bool diceDestroyed = false, uartDestroyed = false;
  int diceDepth = 0, uartDepth = 0, closeResult = 0, closes = 0;
  std::vector<Event> events;
};
Context *context = nullptr;
thread_local unsigned deleteDepth = 0;
std::uintptr_t key(const void *p) {
  return reinterpret_cast<std::uintptr_t>(p);
}
void event(char kind, const void *p, int value = 0) {
  if (context && context->enabled)
    context->events.push_back({kind, key(p), value});
}
int singleton(Dice3Uart *object, Dice3Uart *other) {
  auto *p = SingletonAccess::get();
  if (!p)
    return 0;
  if (p == object)
    return 1;
  require(p == other);
  return 2;
}
struct Receiver : Presonus::DICE::ISysexReceiver {
  void receive(const Presonus::DICE::SysexPacket &) override {
    throw std::runtime_error("unexpected receiver call");
  }
  bool accepts(const Presonus::DICE::SysexPacket &) override {
    throw std::runtime_error("unexpected receiver call");
  }
};
struct Services : presonus::panel::UartServices {
  int closeFile(int fd) override {
    require(context->uartDepth == 1);
    ++context->closes;
    event('F', nullptr, fd);
    return context->closeResult;
  }
  int openFile(const char *, int) override { std::abort(); }
  int readFile(int, void *, std::uint32_t) override { std::abort(); }
  int writeFile(int, const void *, std::uint32_t) override { std::abort(); }
  int exclusive(int, unsigned long) override { std::abort(); }
  int getAttributes(int, termios &) override { std::abort(); }
  void makeRaw(termios &) override { std::abort(); }
  int setSpeed(termios &, speed_t) override { std::abort(); }
  int setAttributes(int, int, const termios &) override { std::abort(); }
  int setFlags(int, int, int) override { std::abort(); }
  void printError(const char *) override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
};
void deleting(void *p) {
  if (!context || !context->enabled)
    return;
  if (context->owner && key(p) == context->owner) {
    require(context->bufferFreed && context->diceDestroyed);
    require(!context->vector || context->vectorFreed);
    context->ownerFreed = true;
  }
  if (p == context->object) {
    require(context->ownerFreed && context->diceDestroyed &&
            context->uartDestroyed);
    require(singleton(context->object, context->other) != 1);
    require(!context->objectFreed);
    context->objectFreed = true;
    event('O', p);
  }
}
} // namespace

extern "C" void __real__ZN4Core8Platform9PosixLockC1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockC1Ev(void *p) {
  __real__ZN4Core8Platform9PosixLockC1Ev(p);
  event('C', p);
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
  if (context && context->enabled) {
    require(key(p) == context->dice || key(p) == context->uart);
    ++(key(p) == context->dice ? context->diceDepth : context->uartDepth);
    event('+', p);
  }
}
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  if (context && context->enabled) {
    require(key(p) == context->dice || key(p) == context->uart);
    int &depth =
        key(p) == context->dice ? context->diceDepth : context->uartDepth;
    require(depth > 0);
    if (key(p) == context->dice)
      require(UartLifetimeAccess::gate(*context->object) == 0xffffffffu);
    --depth;
    event('-', p);
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
extern "C" void __real__ZN4Core8Platform9PosixLockD1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockD1Ev(void *p) {
  if (context && context->enabled) {
    if (key(p) == context->dice) {
      require(context->diceDepth == 0);
      context->diceDestroyed = true;
    } else {
      require(key(p) == context->uart && context->uartDepth == 0 &&
              context->diceDestroyed && context->ownerFreed);
      context->uartDestroyed = true;
    }
    event('D', p);
  }
  __real__ZN4Core8Platform9PosixLockD1Ev(p);
}
extern "C" void __real_core_free(void *);
extern "C" void __wrap_core_free(void *p) {
  if (context && context->enabled && context->buffer &&
      key(p) == context->buffer) {
    require(!context->bufferFreed);
    context->bufferFreed = true;
  }
  __real_core_free(p);
}
extern "C" void __real__ZdaPv(void *);
extern "C" void __wrap__ZdaPv(void *p) {
  if (context && context->enabled && context->vector &&
      key(p) == context->vector) {
    require(!context->vectorFreed && !context->diceDestroyed);
    context->vectorFreed = true;
    event('V', p);
  }
  __real__ZdaPv(p);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (deleteDepth++ == 0)
    deleting(p);
  __real__ZdlPv(p);
  --deleteDepth;
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (deleteDepth++ == 0)
    deleting(p);
  __real__ZdlPvm(p, size);
  --deleteDepth;
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  if (!context || !context->enabled)
    return;
  require(std::string(format) == "UART: close port %d\n");
  va_list args;
  va_start(args, format);
  const int fd = va_arg(args, int);
  va_end(args);
  event('P', nullptr, fd);
}
extern "C" int __wrap_open(const char *, int, ...) { std::abort(); }
extern "C" int __wrap_close(int) { std::abort(); }
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  throw std::runtime_error("no lifetime clock call expected");
}
} // namespace presonus::dice

int main() {
  unsigned total;
  if (!(std::cin >> total))
    return 2;
  for (unsigned index = 0; index < total; ++index) {
    std::string name, mode;
    int fd, capacity, count, instance, closeResult;
    std::uint32_t gate;
    std::cin >> name >> mode >> fd >> gate >> capacity >> count >> instance >>
        closeResult;
    activeCase = name;
    require(bool(std::cin));
    Context c;
    c.closeResult = closeResult;
    context = nullptr;
    Dice3Uart *other = instance == 2 ? new Dice3Uart : nullptr;
    void *memory = ::operator new(sizeof(Dice3Uart));
    auto *object = static_cast<Dice3Uart *>(memory);
    SingletonAccess::set(instance == 1 ? object : other);
    c.object = object;
    c.other = other;
    c.enabled = mode == "c1" || mode == "c2";
    c.constructing = c.enabled;
    context = &c;
    if (mode == "c2")
      dice_c2(memory);
    else
      dice_c1(memory);
    auto &state = UartLifetimeAccess::state(*object);
    if (index == 0)
      std::cerr << "NATIVE_UART_SECONDARY_OFFSET "
                << key(static_cast<UARTComm *>(object)) - key(object) << '\n';
    c.uart = key(&presonus::panel::ProtocolCommAccess::lock(*object));
    c.dice = key(&state.lock);
    c.buffer = key(state.span());
    c.owner = key(UartLifetimeAccess::ownedAddress(*object));
    require(UartLifetimeAccess::ownsState(*object) && c.owner && c.buffer &&
            state.count == 0 && state.span()[64] == 0);
    require(state.receivers.count() == 0 &&
            state.receivers.getCapacity() == 0 &&
            state.receivers.getDelta() == 5);
    require(UartLifetimeAccess::gate(*object) == 0xffffffffu &&
            presonus::panel::UartCommAccess::descriptor(*object) == -1);
    std::ostringstream result;
    if (c.constructing) {
      for (const auto &e : c.events) {
        require(e.kind == 'C' && (e.pointer == c.uart || e.pointer == c.dice));
        result << 'C' << (e.pointer == c.uart ? 'U' : 'D') << ';';
      }
      require(c.events.size() == 2);
      result << "I-1:4294967295:0:0:0:0:5:" << singleton(object, other) << ';';
      c.enabled = false;
      dice_d1(object);
      ::operator delete(memory);
    } else {
      require(state.receivers.resize(capacity));
      require(state.receivers.getCapacity() == capacity);
      std::array<Receiver, 20> receivers;
      require(count >= 0 && count <= capacity && capacity <= 20);
      for (int i = 0; i < count; ++i)
        require(state.receivers.add(i % 3 == 0 ? nullptr : &receivers[i]));
      c.vector = key(state.receivers.getItems());
      UartLifetimeAccess::gate(*object, gate);
      presonus::panel::UartCommAccess::descriptor(*object, fd);
      Services services;
      presonus::panel::UartCommAccess::services(*object, services);
      c.events.clear();
      c.enabled = true;
      if (mode == "d1")
        dice_d1(object);
      else if (mode == "d2")
        dice_d2(object);
      else if (mode == "d0")
        dice_d0(object);
      else if (mode == "t1")
        dice_secondary_destroy(static_cast<UARTComm *>(object));
      else if (mode == "t0")
        dice_secondary_delete(static_cast<UARTComm *>(object));
      else
        throw std::runtime_error("unknown variant");
      require(c.bufferFreed && c.ownerFreed && c.diceDestroyed &&
              c.uartDestroyed && c.diceDepth == 0 && c.uartDepth == 0);
      require(c.vectorFreed == (capacity != 0));
      for (const auto &e : c.events) {
        if (e.kind == '+' || e.kind == '-')
          result << 'L' << (e.pointer == c.dice ? 'D' : 'U') << e.kind << ';';
        else if (e.kind == 'D')
          result << 'D' << (e.pointer == c.dice ? 'D' : 'U') << ';';
        else if (e.kind == 'F' || e.kind == 'P')
          result << e.kind << e.value << ';';
        else {
          require(e.kind == 'V' || e.kind == 'O');
          result << e.kind << ';';
        }
      }
      result << 'S' << singleton(object, other) << ':' << c.closes << ':'
             << c.vectorFreed << ':' << c.objectFreed << ';';
      c.enabled = false;
      if (mode == "d1" || mode == "d2" || mode == "t1") {
        require(!c.objectFreed);
        ::operator delete(memory);
      } else
        require(c.objectFreed);
    }
    context = nullptr;
    SingletonAccess::set(nullptr);
    delete other;
    std::cout << name << ' ' << result.str() << '\n';
  }
}
