#include "presonus/surface/DAWDialogHandler.hpp"
#include "presonus/surface/TransportHandler.hpp"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <new>
using namespace Core::Portable;
namespace {
void *handler = nullptr, *parameter = nullptr;
unsigned frees = 0, paramFrees = 0, destroyed = 0;
long attempts = 0, failAt = -1, live = 0;
bool tracking = false;
void *tracked[4096]{};
void *allocate(std::size_t n) {
  if (tracking && attempts++ == failAt)
    throw std::bad_alloc();
  void *p = std::malloc(n ? n : 1);
  if (!p)
    throw std::bad_alloc();
  if (tracking) {
    for (auto &v : tracked)
      if (!v) {
        v = p;
        ++live;
        return p;
      }
    std::abort();
  }
  return p;
}
void release(void *p) {
  if (!p)
    return;
  if (p == parameter)
    ++paramFrees;
  if (p == handler) {
    assert(paramFrees == 1);
    ++frees;
  }
  for (auto &v : tracked)
    if (v == p) {
      v = nullptr;
      --live;
      break;
    }
  std::free(p);
}
struct Observer : IParamObserver {
  void *castTo(TypeID) override { return nullptr; }
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kDestroyed)
      ++destroyed;
  }
};
struct Handler : Presonus::Surface::TransportHandler {
  void *castTo(TypeID) override { return nullptr; }
  void paramChanged(Parameter *, int) override {}
};
struct InspectDialog : Presonus::Surface::DAWDialogHandler {
  int count() const { return paramList.count(); }
};
struct InspectParam : NumericParam {
  explicit InspectParam(const ParamInfo &i) : NumericParam(i) {}
  int count() const { return observerList.count(); }
  IParamObserver *observer(int i) const { return observerList[i]; }
};
const ParamInfo info = PARAM_TOGGLE(7, "observed", 0, nullptr, 0);
} // namespace
void *operator new(std::size_t n) { return allocate(n); }
void *operator new[](std::size_t n) { return allocate(n); }
void operator delete(void *p) noexcept { release(p); }
void operator delete[](void *p) noexcept { release(p); }
void operator delete(void *p, std::size_t) noexcept { release(p); }
void operator delete[](void *p, std::size_t) noexcept { release(p); }
extern "C" void d1(Presonus::Surface::TransportHandler *) asm(
    "_ZN8Presonus7Surface16TransportHandlerD1Ev");
extern "C" void d0(Presonus::Surface::TransportHandler *) asm(
    "_ZN8Presonus7Surface16TransportHandlerD0Ev");
int main(int argc, char **argv) {
  const int kind = TASK_NUMBER;
  if (kind == 1) {
    assert(argc == 3);
    int old = std::atoi(argv[1]), next = std::atoi(argv[2]);
    Observer a, b, c;
    InspectParam x(info), y(info);
    Handler h;
    x.addObserver(&a);
    y.addObserver(&b);
    Parameter *p[3] = {nullptr, &x, &y};
    Parameter *slot = p[old];
    if (slot) {
      slot->addObserver(&h);
      slot->addObserver(&c);
    }
    h.setAndObserve(slot, p[next]);
    std::printf("%d\n", slot == nullptr ? 0 : slot == &x ? 1 : 2);
    for (auto *q : {&x, &y}) {
      for (int j = 0; j < q->count(); ++j)
        std::printf("%s%d", j ? " " : "",
                    q->observer(j) == &a   ? 11
                    : q->observer(j) == &b ? 22
                    : q->observer(j) == &c ? 33
                                           : 99);
      std::puts("");
    }
    if (slot)
      slot->removeObserver(&h);
  } else if (kind == 4 || kind == 5) {
    Observer observer;
    void *storage = ::operator new(sizeof(Handler));
    auto *h = new (storage) Handler;
    auto *q = new NumericParam(info);
    parameter = q;
    handler = h;
    q->addObserver(&observer);
    h->paramList.add(q);
    if (kind == 4)
      d1(h);
    else
      d0(h);
    assert(destroyed == 1 && paramFrees == 1);
    assert(frees == (kind == 5));
    std::printf("%u %u %u\n", destroyed, paramFrees, frees);
    parameter = nullptr;
    handler = nullptr;
    if (kind == 4)
      ::operator delete(storage);
  } else {
    using Presonus::Surface::DAWDialogHandler;
    if (argc == 2 && std::strcmp(argv[1], "failures") == 0) {
      // Real provider allocation exceptions, independently of native success.
      unsigned failures = 0;
      for (long n = 0; n < 128; ++n) {
        tracking = true;
        failAt = n;
        attempts = 0;
        bool failed = false;
        try {
          InspectDialog d;
        } catch (const std::bad_alloc &) {
          failed = true;
          ++failures;
        }
        tracking = false;
        failAt = -1;
        assert(live == 0);
        if (!failed)
          break;
      }
      assert(failures > 0);
      std::printf("provider allocation failures %u cleanup passed\n", failures);
      return 0;
    }
    InspectDialog d;
    assert(d.sourcePortDAWComponent() == nullptr);
    assert(d.count() == 10);
    for (int j = 0; j < d.count(); ++j) {
      auto *q = d.getParameterAt(j);
      std::printf("%d %d %s %.9g %.9g %.9g\n", q->getType(), q->getTag(),
                  q->getName(), q->getMin(), q->getMax(), q->getDefault());
    }
  }
}
