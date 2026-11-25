#include "presonus/uc/midi_endpoint.hpp"

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <string_view>

using namespace Presonus::UC;
using Access = presonus::uc::MidiEndpointAccess;

namespace {

MidiConnection *connections[4]{};
void *endpointPointer = nullptr;
void *vectorPointer = nullptr;
bool recording = false;
bool failAllocation = false;
int endpointType = 0;
const MidiEvent *activeEvent = nullptr;

int identity(const MidiConnection *connection) {
  for (int i = 0; i < 4; ++i)
    if (connections[i] == connection)
      return i;
  std::abort();
}

void roster(MidiEndpoint &endpoint) {
  for (auto *connection : Access::connections(endpoint))
    std::printf(" %d", identity(connection));
}

class Handler final : public IMidiEventHandler {
public:
  explicit Handler(int number) : number_(number) {}
  void handleMidiEvent(const MidiEvent &event) override {
    if (&event != activeEvent || event.messageWord != 0x903c7f)
      std::abort();
    std::printf("event %d\n", number_);
  }

private:
  int number_;
};

struct Endpoint final : MidiEndpoint {
  int getType() const override {
    if (recording)
      std::puts("type");
    return endpointType;
  }
  void onConnect(MidiConnection *connection, bool added) override {
    std::printf("connect %d %d", identity(connection), added);
    roster(*this);
    std::puts("");
  }
};

void release(void *pointer, bool array) {
  if (recording && array && pointer == vectorPointer) {
    std::puts("release vector");
    vectorPointer = nullptr;
  }
  if (recording && !array && pointer == endpointPointer) {
    std::puts("release receiver");
    endpointPointer = nullptr;
  }
}

[[gnu::noipa]] void deleteEndpoint(MidiEndpoint *value) { delete value; }

void seed(MidiEndpoint &endpoint, std::string_view rosterIds) {
  for (const char id : rosterIds)
    if (!Access::connections(endpoint).add(connections[id - '0']))
      std::abort();
}

void reportRoster(MidiEndpoint &endpoint) {
  std::printf("result");
  roster(endpoint);
  std::puts("");
}

} // namespace

extern "C" void *__real__Znam(std::size_t);
extern "C" void *__wrap__Znam(std::size_t size) {
  if (recording) {
    std::printf("allocate %zu\n", size / sizeof(MidiConnection *));
    if (failAllocation)
      throw std::bad_alloc();
  }
  return __real__Znam(size);
}
extern "C" void __real__ZdaPv(void *);
extern "C" void __wrap__ZdaPv(void *pointer) {
  release(pointer, true);
  __real__ZdaPv(pointer);
}
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void __wrap__ZdaPvm(void *pointer, std::size_t size) {
  release(pointer, true);
  __real__ZdaPvm(pointer, size);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *pointer) {
  release(pointer, false);
  __real__ZdlPv(pointer);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  release(pointer, false);
  __real__ZdlPvm(pointer, size);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view operation = argv[1];
  const int index = std::atoi(argv[2]);
  Handler handler1(1), handler3(3);
  MidiConnection first, second, third;
  connections[1] = &first;
  connections[2] = &second;
  connections[3] = &third;
  first.setPortableHandler(&handler1);
  third.setPortableHandler(operation == "send_from" ? &handler3 : &handler1);
  alignas(Endpoint) std::byte memory[sizeof(Endpoint)];
  std::memset(memory, index ? 0xa5 : 0, sizeof memory);
  const bool deleting = operation == "deleting_destroy";
  auto *endpoint = deleting ? new Endpoint : new (memory) Endpoint;
  endpointPointer = endpoint;
  if (operation == "complete_construct" || operation == "base_construct") {
    MidiEndpointInfo info;
    endpoint->getInfo(info);
    if (!info.firstName || !info.secondName)
      std::abort();
    const auto &vector = Access::connections(*endpoint);
    std::printf("result %d %d %d %d %d %d %d\n", *info.firstName,
                *info.secondName, info.firstId, info.secondId, vector.count(),
                vector.getCapacity(), vector.getDelta());
  } else if (operation == "get_info") {
    constexpr const char *firstNames[] = {"", "Input",
                                          "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ"};
    constexpr const char *secondNames[] = {"", "Output", "Secondary"};
    constexpr int firstIds[] = {0, 17, -2147483647 - 1};
    constexpr int secondIds[] = {0, -31, 2147483647};
    constexpr int types[] = {0, 13, -17};
    Access::setInfo(*endpoint, firstIds[index], secondIds[index],
                    firstNames[index], secondNames[index]);
    endpointType = types[index];
    MidiEndpointInfo info, again;
    info.preserved = 0x35353535;
    recording = true;
    endpoint->getInfo(info);
    recording = false;
    endpoint->getInfo(again);
    if (info.firstName != again.firstName ||
        info.secondName != again.secondName)
      std::abort();
    std::printf("result %d %d %d %d \"%s\" \"%s\"\n", info.preserved, info.type,
                info.firstId, info.secondId, info.firstName, info.secondName);
  } else if (operation == "find_connection_for_handler") {
    constexpr const char *rosters[] = {"", "23", "213", "21", "13"};
    IMidiEventHandler *handlers[] = {&handler1, &handler1, &handler1, &handler3,
                                     nullptr};
    seed(*endpoint, rosters[index]);
    std::printf("result %d\n",
                identity(endpoint->findConnectionForHandler(handlers[index])));
  } else if (operation == "send_from") {
    constexpr const char *rosters[] = {"", "213", "31", "2"};
    seed(*endpoint, rosters[index]);
    MidiEvent event;
    event.messageWord = 0x903c7f;
    activeEvent = &event;
    const bool result = endpoint->sendFrom(event);
    std::printf("result %d\n", result);
  } else if (operation == "add_connection") {
    constexpr const char *rosters[] = {"", "2", "12121", "21212"};
    seed(*endpoint, rosters[index]);
    failAllocation = index == 3;
    vectorPointer = Access::connections(*endpoint).getItems();
    recording = true;
    endpoint->addConnection(&third);
    recording = false;
    reportRoster(*endpoint);
  } else if (operation == "remove_connection") {
    constexpr const char *rosters[] = {"", "23", "213", "121", "21"};
    seed(*endpoint, rosters[index]);
    endpoint->removeConnection(&first);
    reportRoster(*endpoint);
  } else if (operation == "base_destroy" || operation == "complete_destroy" ||
             deleting) {
    if (index)
      seed(*endpoint, "21");
    vectorPointer = Access::connections(*endpoint).getItems();
    recording = true;
    if (deleting)
      deleteEndpoint(endpoint);
    else if (operation == "base_destroy")
      endpoint->~Endpoint();
    else
      endpoint->MidiEndpoint::~MidiEndpoint();
    recording = false;
    if (deleting != (endpointPointer == nullptr) || vectorPointer ||
        first.portableHandler() != &handler1 ||
        third.portableHandler() != &handler1)
      std::abort();
    std::puts("result");
    return 0;
  } else {
    return 2;
  }
  endpoint->~Endpoint();
}
