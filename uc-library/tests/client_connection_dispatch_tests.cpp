#include "presonus/uc/client_event_values.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
#include <iostream>
#include <stdexcept>
#include <string>
using namespace Presonus::UC;
namespace {
std::string calls;
void *watched = nullptr;
unsigned frees = 0;
const Event *expectedHeader = nullptr;
const unsigned char *expectedSamples = nullptr;
unsigned identityChecks = 0;
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
void log(const char *name, std::initializer_list<unsigned> args) {
  if (!calls.empty())
    calls += ';';
  calls += name;
  calls += ':';
  bool first = true;
  for (auto v : args) {
    if (!first)
      calls += ',';
    first = false;
    calls += std::to_string(v);
  }
}
#include "client_dispatch_transport.hpp"
struct Files final : IFileTransferManager {
  int handleEvent(void *p, const Event &) override {
    log("file",
        {static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(p)), 1});
    return 456;
  }
  int cancelForHandler(int a, unsigned char b) override {
    log("cancel", {static_cast<unsigned>(a), b});
    return -11;
  }
  int sendRequest(FileRequestEvent &, IFileRequestHandler *, int) override {
    std::abort();
  }
  int acceptRequest(IFileRequestHandler *, int,
                    const FileRequestEvent &) override {
    std::abort();
  }
  int sendCancel(IFileRequestHandler *) override { std::abort(); }
  int setTransferPriority(int) override { std::abort(); }
  int setDataRateLimit(IFileRequestHandler *, int) override { std::abort(); }
  int enableDataRateReporting(unsigned char) override { std::abort(); }
  bool isBusy() const override { std::abort(); }
};
struct Client final : ClientImplementation {
  Client(NativeTransport &n, Files &f, presonus::uc::EventOrigins &o,
         presonus::uc::ClientTypedOrigins &t)
      : ClientImplementation(presonus::uc::ClientDispatchPortTag{}, n, f, o, t,
                             0x11223344, 0xaabbccdd) {}
  std::uint64_t getSystemTime() const override { return 0; }
  void updateLevels(const MeterEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    require(v.data == expectedSamples, "meter payload identity changed");
    log("callback", {4});
  }
  void receiveEvent(const TimeCodeEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    log("callback", {5});
  }
  void receiveEvent(const ParamEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    std::visit(
        [](auto *p) {
          require(&p->header == expectedHeader,
                  "param payload identity changed");
        },
        v.payload);
    log("callback", {6});
  }
  void receiveEvent(const MessageEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    log("callback", {7});
  }
  void receiveEvent(const BinaryEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    log("callback", {8});
  }
  void receiveEvent(const DebugEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    log("callback", {9});
  }
  void receiveEvent(const LoopbackReplyEvent &v) override {
    require(&v.header == expectedHeader, "callback header identity changed");
    ++identityChecks;
    log("callback", {10});
  }
  void sendAllToServer() override { std::abort(); }
};
#include "client_dispatch_cases.hpp"
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched) {
    ++frees;
    log("delete", {1});
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == watched) {
    ++frees;
    log("delete", {1});
  }
  __real__ZdlPvm(p, n);
}
int main() {
  try {
    unsigned cases = 0;
    for (const auto &x : dispatchCases) {
      NativeTransport network;
      Files files;
      presonus::uc::EventOrigins origins;
      presonus::uc::ClientTypedOrigins typed;
      auto *client = new Client(network, files, origins, typed);
      presonus::uc::ClientStatePortAccess::untouchedBits(*client) =
          0x0123456789abcd00ull | x.flag;
      Event plain{x.tag, 0x50607080, 0x90abcdef, 0xfedcba09};
      Event *event = &plain;
      ParamValueEvent value;
      ParamStringEvent string;
      ParamColorEvent color;
      ParamRangeEvent range;
      ParamStringListEvent list;
      MeterEvent8 m8;
      MeterEvent16 m16;
      TimeCodeEvent time;
      MessageEvent message;
      BinaryEvent binary;
      DebugEvent debug;
      presonus::uc::EventOrigins::Binding origin;
      presonus::uc::ClientTypedOrigins::Binding binding;
      switch (x.tag) {
      case 20566:
        value.header = plain;
        origin = origins.bind(value);
        event = &value.header;
        break;
      case 20563:
        string.header = plain;
        origin = origins.bind(string);
        event = &string.header;
        break;
      case 20547:
        color.header = plain;
        origin = origins.bind(color);
        event = &color.header;
        break;
      case 20562:
        range.header = plain;
        origin = origins.bind(range);
        event = &range.header;
        break;
      case 20556:
        list.header = plain;
        origin = origins.bind(list);
        event = &list.header;
        break;
      case 19778:
        m8.header = plain;
        origin = origins.bind(m8);
        event = &m8.header;
        break;
      case 19795:
        m16.header = plain;
        origin = origins.bind(m16);
        event = &m16.header;
        break;
      case 21571:
        time.header = plain;
        binding = typed.bind(time);
        event = &time.header;
        break;
      case 19021:
      case 21826:
      case 23106:
      case 23117:
        message.header = plain;
        binding = typed.bind(message);
        event = &message.header;
        break;
      case 16975:
        binary.header = plain;
        binding = typed.bind(binary);
        event = &binary.header;
        break;
      case 17474:
        debug.header = plain;
        binding = typed.bind(debug);
        event = &debug.header;
        break;
      }
      expectedHeader = event;
      expectedSamples = x.tag == 19778   ? m8.data.data()
                        : x.tag == 19795 ? m16.data.data()
                                         : nullptr;
      calls.clear();
      unsigned result = 0;
      const std::string action = x.action;
      bool dead = false;
      message.header = plain;
      if (action == "connect")
        result = client->connect(static_cast<int>(x.route), message);
      else if (action == "disconnect")
        result = client->disconnect(x.null ? nullptr : &message);
      else if (action == "dispatch")
        result = client->handleEvent(
            reinterpret_cast<void *>(std::uintptr_t{0xdeadbeef}), *event);
      else if (action == "D0") {
        watched = client;
        ClientImplementation *base = client;
        delete base;
        watched = nullptr;
        dead = true;
      } else {
        client->~Client();
        ::operator delete(client);
        dead = true;
      }
      require(calls == x.calls, "original boundary trace differs");
      if (!dead) {
        require(result == x.result, "original result bits differ");
        require(presonus::uc::ClientStatePortAccess::routeB(*client) ==
                    x.routeB,
                "original routeB differs");
        require(presonus::uc::ClientStatePortAccess::untouchedBits(*client) ==
                    x.untouched,
                "upper56/flag differs");
        delete client;
      }
      ++cases;
    }

    // App-owned provenance domain tests beyond the original ARM dispatch cases.
    // Every manual referent remains alive until its token is reset.
    using Origins = presonus::uc::ClientTypedOrigins;
    Origins typed;
    TimeCodeEvent time;
    time.header.type = 21571;
    auto first = typed.bind(time);
    require(bool(first), "valid typed bind failed");
    require(!typed.bind(time), "duplicate binding accepted");
    require(typed.get<TimeCodeEvent>(&time.header) == &time,
            "typed identity lost");
    require(!typed.get<DebugEvent>(&time.header),
            "mismatched typed access accepted");
    auto moved = std::move(first);
    require(!first && bool(moved), "binding move changed ownership");
    first.reset();
    require(typed.get<TimeCodeEvent>(&time.header) == &time,
            "moved-from reset unbound owner");
    time.header.type = 17474;
    require(!typed.get<TimeCodeEvent>(&time.header) && !moved,
            "mutated tag accepted");
    time.header.type = 21571;
    require(bool(moved), "restored tag lost live origin");
    moved.reset();
    require(!typed.get<TimeCodeEvent>(&time.header), "reset kept stale origin");
    Event forged;
    forged.type = 21571;
    require(!typed.get<TimeCodeEvent>(&forged),
            "tag-only forged header accepted");
    DebugEvent wrong;
    wrong.header.type = 21571;
    require(!typed.bind(wrong), "wrong typed tag accepted");
    Origins::Binding survivor;
    {
      Origins temporary;
      survivor = temporary.bind(time);
      require(bool(survivor), "temporary bind failed");
    }
    require(!survivor, "token survived expired registry");
    survivor.reset();
    auto *heap = new TimeCodeEvent;
    heap->header.type = 21571;
    auto heapToken = typed.bind(*heap);
    const Event *stale = &heap->header;
    heapToken.reset();
    delete heap;
    require(!typed.get<TimeCodeEvent>(stale),
            "unbound dead address dereferenced/accepted");
    NativeTransport network;
    Files files;
    presonus::uc::EventOrigins params;
    Client client(network, files, params, typed);
    calls.clear();
    require(client.handleEvent(nullptr, forged) == -1 && calls.empty(),
            "unbound typed callback dispatched");
    {
      auto bound = typed.bind(time);
      expectedHeader = &time.header;
      calls.clear();
      require(client.handleEvent(nullptr, time.header) == 0,
              "typed callback failed");
      require(calls == "callback:5", "typed callback wrong");
    }
    calls.clear();
    require(client.handleEvent(nullptr, time.header) == -1 && calls.empty(),
            "expired binding dispatched");
    ParamValueEvent param;
    param.header.type = 20566;
    expectedHeader = &param.header;
    {
      auto bound = params.bind(param);
      calls.clear();
      require(client.handleEvent(nullptr, param.header) == 0,
              "param bridge callback failed");
    }
    calls.clear();
    require(client.handleEvent(nullptr, param.header) == -1 && calls.empty(),
            "expired param bridge dispatched");

    require(frees == 2, "actual D0 frees missing");
    std::cout << "PASS original_app_cases=" << cases
              << " actual_deleting_destructor_frees=" << frees
              << " concrete_typed_origins=true identity_checks="
              << identityChecks << " binding_lifetime_checks=18\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
