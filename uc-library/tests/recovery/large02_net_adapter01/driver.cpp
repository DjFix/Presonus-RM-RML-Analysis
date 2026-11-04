#include "presonus/uc/adapter_handler.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>

static bool track;
static void *allocation;
static void *trackedAllocations[4];
static int allocations, frees;
void *operator new(std::size_t size) {
  void *p = std::malloc(size);
  if (!p)
    throw std::bad_alloc();
  if (track) {
    allocation = p;
    if (allocations >= 4)
      std::abort();
    trackedAllocations[allocations++] = p;
  }
  return p;
}
void operator delete(void *p) noexcept {
  for (auto &entry : trackedAllocations)
    if (p && p == entry) {
      ++frees;
      entry = nullptr;
      if (p == allocation)
        allocation = nullptr;
      break;
    }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
// These are abort boundaries, not successful network test doubles.
extern "C" int __wrap_getifaddrs(void *) { std::abort(); }
extern "C" int __wrap_gethostname(char *, std::size_t) { std::abort(); }
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" int __wrap_connect(int, const void *, unsigned) { std::abort(); }
extern "C" int __wrap_getaddrinfo(const char *, const char *, const void *,
                                  void *) {
  std::abort();
}
extern "C" void *__wrap_gethostbyname(const char *) { std::abort(); }
extern "C" int __wrap_getnameinfo(const void *, unsigned, char *, unsigned,
                                  char *, unsigned, int) {
  std::abort();
}

static std::string hex(const void *p, std::size_t n) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  for (std::size_t i = 0; i < n; ++i) {
    auto b = static_cast<const unsigned char *>(p)[i];
    result += digits[b >> 4];
    result += digits[b & 15];
  }
  return result;
}
struct Derived : Presonus::UC::AdapterHandler {};
static void output(const presonus::uc::AdapterHandlerState &s) {
  std::cout << "{\"suffix_empty\":" << (s.suffix.str()[0] == 0)
            << ",\"primary_empty\":" << (s.primaryText.str()[0] == 0)
            << ",\"multi\":" << unsigned(s.multiAddress)
            << ",\"suspended\":" << unsigned(s.suspended)
            << ",\"valid\":" << unsigned(s.cacheValid)
            << ",\"changed\":" << unsigned(s.changed)
            << ",\"interval\":" << s.refreshIntervalBits
            << ",\"counter\":" << s.processCounterBits
            << ",\"count\":" << s.storage.count << ",\"addresses\":\""
            << hex(s.storage.values.data(), sizeof(s.storage.values))
            << "\"}\n";
}
int main(int argc, char **argv) {
  std::string mode = argc > 1 ? argv[1] : "C1";
  if (mode == "borrowed") {
    presonus::uc::CclAdapterServices provider;
    presonus::uc::AdapterHandlerState state(provider);
    state.refreshIntervalBits = 1000;
    state.processCounterBits = 21;
    state.suffix = "borrowed";
    {
      Presonus::UC::AdapterHandler facade(presonus::uc::AdapterSourcePortTag{},
                                          state);
      if (&facade.sourcePortState() != &state)
        return 4;
    }
    if (state.refreshIntervalBits != 1000 || state.processCounterBits != 21 ||
        std::strcmp(state.suffix.str(), "borrowed"))
      return 5;
    std::cout << "{\"borrowed_preserved\":true}\n";
    return 0;
  }
  if (mode == "singleton") {
    auto &a = presonus::uc::sourceAdapterSingleton();
    auto &b = presonus::uc::sourceAdapterSingleton();
    if (&a != &b)
      return 7;
    output(a.sourcePortState());
    return 0;
  }
  bool ticks = mode.rfind("ticks-", 0) == 0;
  if (ticks)
    mode = mode.substr(6);
  if (mode == "C1") {
    track = true;
    auto *p = new Presonus::UC::AdapterHandler;
    track = false;
    // The outer allocation and owned state must both be genuinely freed.
    void *inner = allocation;
    if (ticks)
      for (int i = 0; i < 101; ++i)
        p->process();
    output(p->sourcePortState());
    delete p;
    if (!inner || allocations != 2 || frees != 2 || allocation)
      return 8;
  } else if (mode == "C2") {
    track = true;
    {
      Derived p;
      track = false;
      if (ticks)
        for (int i = 0; i < 101; ++i)
          p.process();
      output(p.sourcePortState());
    }
    if (allocations != 1 || frees != 1 || allocation)
      return 9;
  } else
    return 2;
}
