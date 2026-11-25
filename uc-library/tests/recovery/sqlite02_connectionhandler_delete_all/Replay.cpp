#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/external_connection.hpp"
#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string_view>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
std::ostringstream trace;
bool observed = false;
std::array<void *, 4> allocated{};
std::array<bool, 4> released{};

int identity(void *pointer) {
  if (!pointer)
    return 0;
  auto entry = std::find(allocated.begin() + 1, allocated.end(), pointer);
  if (entry == allocated.end())
    std::abort();
  return static_cast<int>(entry - allocated.begin());
}

struct ConnectionFixture {
  ExternalConnectionState external;
  ConnectionState common;
  BasicConnectionState outgoing;
  HandlerConnectionView view;
};

class TrackedConnection final : public ExternalConnection {
public:
  TrackedConnection(ConnectionFixture &fixture, int identifier)
      : ExternalConnection(fixture.external, fixture.common, fixture.outgoing),
        identifier_(identifier) {}
  ~TrackedConnection() override {
    if (observed) {
      trace << " destroy:" << identifier_;
      observeDestruction();
    }
  }
  static void *operator new(std::size_t size) { return ::operator new(size); }
  static void operator delete(void *pointer) {
    const int identifier = identity(pointer);
    if (released[identifier])
      std::abort();
    released[identifier] = true;
    if (observed)
      trace << " deallocate:" << identifier;
    ::operator delete(pointer);
  }
  bool process(bool) override { std::abort(); }

private:
  int identifier_;
  static void observeDestruction();
};

void printRoster(std::ostream &out, const Core::Vector<Connection *> &roster) {
  out << '[';
  for (int index = 0; index < roster.count(); ++index) {
    if (index)
      out << ',';
    out << identity(roster.at(index));
  }
  out << ']';
}

void seed(ConnectionHandlerState &state, Core::Vector<Connection *> &roster,
          std::array<ConnectionFixture, 4> &objects, std::string_view ids) {
  for (auto id : ids) {
    const int identifier = id - '0';
    if (identifier < 0 || identifier >= static_cast<int>(objects.size()))
      std::abort();
    if (!identifier) {
      roster.add(nullptr);
      continue;
    }
    auto &fixture = objects[identifier];
    if (allocated[identifier])
      std::abort();
    auto *connection = new TrackedConnection(fixture, identifier);
    allocated[identifier] = connection;
    fixture.view.identity = connection;
    fixture.view.common = &fixture.common;
    fixture.view.outgoing = connection;
    roster.add(connection);
    state.views.add(&fixture.view);
  }
}

void cleanupFixtures() {
  for (std::size_t id = 1; id < allocated.size(); ++id) {
    if (allocated[id] && !released[id])
      delete static_cast<TrackedConnection *>(allocated[id]);
  }
}

void checkViews(const ConnectionHandlerState &state) {
  for (auto *view : state.views)
    if (released[identity(view->identity)])
      std::abort();
}

void TrackedConnection::observeDestruction() {}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::array<ConnectionFixture, 4> objects;
  ConnectionHandlerState state;
  ConnectionHandler handler(state);
  Core::Vector<Connection *> roster(5);
  Core::Vector<int> untouched{17, 23};
  seed(state, roster, objects, argv[1]);
  observed = true;
  handler.deleteAll(roster);
  observed = false;
  if (roster.getCapacity() || untouched.count() != 2 || untouched.at(0) != 17 ||
      untouched.at(1) != 23)
    return 3;
  checkViews(state);
  printRoster(std::cout, roster);
  std::cout << trace.str() << '\n';
  cleanupFixtures();
}
