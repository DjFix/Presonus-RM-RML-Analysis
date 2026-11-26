#include "presonus/avb/manager_transport.hpp"
#if !defined(AVB_PROVIDER_BRIDGE) && !defined(AVB_REPLAY_RM)
#include "presonus/avb/dice_manager_transport.hpp"
#endif
#if !defined(AVB_PROVIDER_BRIDGE) && !defined(AVB_REPLAY_CS18)
#include "presonus/avb/noaa_manager_transport.hpp"
#endif
#include "presonus/avb/receive_services.hpp"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <deque>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" long long avb_clock_bridge(long long ticks) {
  return ticks / 1000000;
}

extern "C" void avb_format_bridge(char *buffer, const char *format,
                                  unsigned value) {
  Core::CString256 text(buffer);
  text.appendFormat(format, value);
  std::memcpy(buffer, text.str(), text.length() + 1);
}
extern "C" unsigned long long avb_scan_bridge(const char *text) {
  unsigned long long result = 0;
  std::sscanf(text, "%llx", &result);
  return result;
}
#ifndef AVB_PROVIDER_BRIDGE
static std::vector<void *> watchedStreams;
static unsigned freedStreams = 0;
static void recordDelete(void *p) {
  const auto found = std::find(watchedStreams.begin(), watchedStreams.end(), p);
  if (found != watchedStreams.end()) {
    ++freedStreams;
    watchedStreams.erase(found);
  }
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  recordDelete(p);
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  recordDelete(p);
  __real__ZdlPvm(p, n);
}
using Presonus::AVB::AvbListener;
using Presonus::AVB::AvbManagerBase;
using Presonus::AVB::AvbTalker;
struct Captures {
  std::vector<std::vector<unsigned char>> sent;
  std::deque<unsigned char> incoming;
  int status = 1;
  void capture(const unsigned char *p, unsigned n) {
    sent.emplace_back(p, p + n);
    if (status >= 0)
      incoming = {0xf0, 0x23, static_cast<unsigned char>(status), 0xf7};
  }
};
#if !defined(AVB_REPLAY_RM)
struct UartIO final : presonus::panel::UartServices {
  Captures &c;
  explicit UartIO(Captures &c) : c(c) {}
  int openFile(const char *, int) override {
    throw std::runtime_error("unexpected open");
  }
  int closeFile(int) override { return 0; }
  int readFile(int, void *b, std::uint32_t n) override {
    unsigned i = 0;
    for (; i < n && !c.incoming.empty(); ++i) {
      static_cast<unsigned char *>(b)[i] = c.incoming.front();
      c.incoming.pop_front();
    }
    return i;
  }
  int writeFile(int, const void *p, std::uint32_t n) override {
    c.capture(static_cast<const unsigned char *>(p), n);
    return n;
  }
  int exclusive(int, unsigned long) override {
    throw std::runtime_error("unexpected ioctl");
  }
  int getAttributes(int, termios &) override {
    throw std::runtime_error("unexpected termios");
  }
  void makeRaw(termios &) override {
    throw std::runtime_error("unexpected termios");
  }
  int setSpeed(termios &, speed_t) override {
    throw std::runtime_error("unexpected termios");
  }
  int setAttributes(int, int, const termios &) override {
    throw std::runtime_error("unexpected termios");
  }
  int setFlags(int, int, int) override {
    throw std::runtime_error("unexpected fcntl");
  }
  void printError(const char *) override {
    throw std::runtime_error("unexpected error");
  }
  std::int64_t rawTicks() override { return 123000000; }
};
#endif
#if !defined(AVB_REPLAY_CS18)
struct SpiIO final : presonus::noaa::SpiServiceIO {
  Captures &c;
  explicit SpiIO(Captures &c) : c(c) {}
  int open(const char *, int) override {
    throw std::runtime_error("unexpected open");
  }
  int maxSpeed(int, std::uint32_t) override {
    throw std::runtime_error("unexpected ioctl");
  }
  int transfer(int, const presonus::noaa::SpiTransfer &t) override {
    if (t.length && t.tx[0] == 0xf0)
      c.capture(t.tx, t.length);
    for (unsigned i = 0; i < t.length; ++i) {
      t.rx[i] = c.incoming.empty() ? 0xf8 : c.incoming.front();
      if (!c.incoming.empty())
        c.incoming.pop_front();
    }
    return t.length;
  }
  int close(int) override { return 0; }
  int errorNumber() override { return 0; }
  std::int64_t rawTicks() override { return 123000000; }
  void diagnostic(bool, const char *, int, bool) override {}
};
#endif
#if !defined(AVB_REPLAY_RM)
struct Callbacks final : presonus::dice::AssemblyCallbacks {
  void noReceiver(unsigned) override {}
  void packetLog(const Presonus::DICE::SysexPacket &) override {}
  void sourcePortError(presonus::dice::AssemblyError, unsigned) override {
    throw std::runtime_error("assembly error");
  }
};
struct UartAccess : Presonus::DICE::Dice3Uart {
  static void bind(Presonus::DICE::Dice3Uart *uart) { theInstance = uart; }
};
#endif
struct Pump final : presonus::dice::IdlePump {
#if !defined(AVB_REPLAY_RM)
  Presonus::DICE::Dice3Uart *uart = nullptr;
#endif
#if !defined(AVB_REPLAY_CS18)
  Presonus::NOAA::TCardSPI *spi = nullptr;
#endif
  void onIdle(bool force) override {
#if !defined(AVB_REPLAY_RM)
    if (uart)
      uart->onIdle();
#endif
#if !defined(AVB_REPLAY_CS18)
    if (spi)
      spi->onIdle(force);
#endif
  }
};
static void array(std::ostream &out, const std::vector<unsigned char> &v) {
  out << '[';
  for (unsigned i = 0; i < v.size(); ++i) {
    if (i)
      out << ',';
    out << unsigned(v[i]);
  }
  out << ']';
}
int main(int argc, char **argv) {
  if (argc > 1 && std::string(argv[1]) == "--preconditions") {
    AvbManagerBase manager;
    presonus::avb::ReceiveContext context;
    manager.bindReceiveContext(context, AvbManagerBase::Role::Cs18Client);
    unsigned passed = 0;
    if (manager.sendAvbSysex(0x23, nullptr, 31) == -1)
      ++passed;
    try {
      manager.sendAvbSysex(0x23, nullptr, 0);
    } catch (const std::logic_error &) {
      ++passed;
    }
    try {
      manager.sendAvbSysex(0x23, nullptr, -1);
    } catch (const std::invalid_argument &) {
      ++passed;
    }
    manager.stopAvb();
    if (context.processingWord == 0)
      ++passed;
    std::cout << passed << " portable precondition cases\n";
    return passed == 4 ? 0 : 1;
  }
  try {
    std::string line;
    while (std::getline(std::cin, line)) {
      std::istringstream in(line);
      std::string op, role, text;
      int processing, status;
      unsigned na, nl, nt, np;
      in >> op >> role >> processing >> status >> std::quoted(text) >> na;
      std::vector<unsigned long long> args(na);
      for (auto &x : args)
        in >> x;
      presonus::avb::ReceiveContext context;
      context.processingWord = processing;
      in >> nl;
      for (unsigned i = 0; i < nl; ++i) {
        unsigned id, suffix;
        unsigned long long key;
        int n;
        in >> id >> key >> suffix >> n;
        context.listeners.append(new AvbListener(id, key, suffix, n));
      }
      in >> nt;
      for (unsigned i = 0; i < nt; ++i) {
        unsigned id;
        int n;
        in >> id >> n;
        context.talkers.append(new AvbTalker(id, n));
      }
      in >> np;
      std::vector<unsigned char> payload(np);
      for (auto &x : payload) {
        unsigned n;
        in >> n;
        x = n;
      }
      if (!in)
        throw std::runtime_error("input parse");
      Captures capture;
      capture.status = status;
      const bool client = role == "client";
#if defined(AVB_REPLAY_CS18)
      if (!client)
        throw std::runtime_error("CS18 executable received RM case");
#endif
#if defined(AVB_REPLAY_RM)
      if (client)
        throw std::runtime_error("RM executable received CS18 case");
#endif
#if !defined(AVB_REPLAY_RM)
      UartIO uartIO(capture);
      Callbacks callbacks;
      presonus::dice::UartAssemblyState us({}, 0, 8);
      Presonus::DICE::Dice3Uart uart(us, callbacks);
      presonus::panel::UartCommAccess::services(uart, uartIO);
      presonus::panel::UartCommAccess::descriptor(uart, 7);
      UartAccess::bind(&uart);
#endif
#if !defined(AVB_REPLAY_CS18)
      SpiIO spiIO(capture);
      presonus::noaa::SpiPacketState ss({}, 0, 0, 8);
      Presonus::NOAA::TCardSPI spi(ss);
      presonus::noaa::SpiServiceAccess::bind(spi, spiIO, 8, {}, 0);
      presonus::noaa::SpiServiceAccess::singleton(&spi);
#endif
      Pump pump;
#if !defined(AVB_REPLAY_RM)
      pump.uart = client ? &uart : nullptr;
#endif
#if !defined(AVB_REPLAY_CS18)
      pump.spi = client ? nullptr : &spi;
#endif
      AvbManagerBase manager;
      manager.bindReceiveContext(context, client
                                              ? AvbManagerBase::Role::Cs18Client
                                              : AvbManagerBase::Role::RmServer);
      std::unique_ptr<presonus::avb::ManagerTransport> transport;
#if !defined(AVB_REPLAY_RM)
      if (client)
        transport = std::make_unique<presonus::avb::DiceManagerTransport>(
            manager, uart, pump);
#endif
#if !defined(AVB_REPLAY_CS18)
      if (!client)
        transport = std::make_unique<presonus::avb::NoaaManagerTransport>(
            manager, spi, pump);
#endif
      manager.bindTransport(*transport);
      watchedStreams.clear();
      for (auto *p : context.listeners)
        watchedStreams.push_back(p);
      for (auto *p : context.talkers)
        watchedStreams.push_back(p);
      freedStreams = 0;
      long long result = 0;
      bool noResult = false;
      Core::CString256 mac(text.c_str());
      if (op == "resizeListener")
        result = manager.resizeListener(args[0], args[1]);
      else if (op == "resizeTalker")
        result = manager.resizeTalker(args[0], args[1]);
      else if (op == "publish")
        result = manager.publish(args[0], args[1]);
      else if (op == "subscribe")
        result = manager.subscribe(args[0], args[1]);
      else if (op == "setAudioClockToListener")
        result = manager.setAudioClockToListener(
            args[0] == ~0ull ? nullptr : context.listeners.getFirst());
      else if (op == "configureMasterFirewireRecording")
        result = manager.configureMasterFirewireRecording(args[0]);
      else if (op == "startAvb")
        result = manager.startAvb(args[0], args[1], args[2]);
      else if (op == "stopAvb") {
        manager.stopAvb();
        noResult = true;
      } else if (op == "addListener") {
        auto *p = manager.addListener(args[0], args[1], args[2]);
        result = p ? p->inspectState().identifierByte : -1;
      } else if (op == "addTalker") {
        auto *p = manager.addTalker(args[0]);
        result = p ? p->inspectState().identifierByte : -1;
      } else if (op == "removeListener") {
        AvbListener foreign(99, 1, 2, 3);
        auto *p = &foreign;
        unsigned i = 0;
        for (auto *x : context.listeners) {
          if (i++ == args[0])
            p = x;
        }
        manager.removeListener(args[0] == ~0ull ? nullptr : p);
        noResult = true;
      } else if (op == "removeTalker") {
        AvbTalker foreign(99, 3);
        auto *p = &foreign;
        unsigned i = 0;
        for (auto *x : context.talkers) {
          if (i++ == args[0])
            p = x;
        }
        manager.removeTalker(args[0] == ~0ull ? nullptr : p);
        noResult = true;
      } else if (op == "removeAllListeners") {
        manager.removeAllListeners();
        noResult = true;
      } else if (op == "sendAvbSysex")
        result = manager.sendAvbSysex(args[0], payload.data(),
                                      static_cast<int>(args[1]));
#if !defined(AVB_REPLAY_CS18)
      else if (op == "accepts") {
        Presonus::NOAA::SysexPacket p;
        p.length = args[0];
        p.bytes[1] = args[1];
        result = manager.accepts(p);
      }
#endif
      else if (op == "macAddressToString") {
        manager.macAddressToString(mac, args[0]);
        noResult = true;
      } else if (op == "macAddressStringToLong")
        result = manager.macAddressStringToLong(mac);
      else
        throw std::runtime_error("unknown operation");
      std::cout << "{\"result\":";
      if (noResult)
        std::cout << "null";
      else
        std::cout << result;
      std::cout << ",\"deleted_streams\":" << freedStreams;
      watchedStreams.clear();
      std::cout << ",\"packets\":[";
      for (unsigned i = 0; i < capture.sent.size(); ++i) {
        if (i)
          std::cout << ',';
        array(std::cout, capture.sent[i]);
      }
      std::cout << "],\"listeners\":[";
      bool first = true;
      for (auto *p : context.listeners) {
        auto s = p->inspectState();
        if (!first)
          std::cout << ',';
        first = false;
        std::cout << '[' << unsigned(s.identifierByte) << ',' << s.identifier
                  << ',' << s.suffix << ',' << s.integerWord << ']';
      }
      std::cout << "],\"talkers\":[";
      first = true;
      for (auto *p : context.talkers) {
        auto s = p->inspectState();
        if (!first)
          std::cout << ',';
        first = false;
        std::cout << '[' << unsigned(s.identifierByte) << ',' << s.integerWord
                  << ']';
      }
      std::cout << "],\"processing\":" << context.processingWord
                << ",\"text\":";
      if (op.find("macAddress") == 0)
        std::cout << std::quoted(mac.str());
      else
        std::cout << "null";
      std::cout << "}\n";
      manager.removeAllListeners();
      for (auto *p : context.talkers)
        delete p;
      context.talkers.removeAll();
      transport.reset();
#if !defined(AVB_REPLAY_RM)
      UartAccess::bind(nullptr);
#endif
#if !defined(AVB_REPLAY_CS18)
      presonus::noaa::SpiServiceAccess::singleton(nullptr);
#endif
    }
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
#endif
