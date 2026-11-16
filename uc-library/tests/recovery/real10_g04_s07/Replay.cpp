#include "presonus/TargetedComponent.hpp"
#include <iostream>
#include <string>
struct Instrumented : Presonus::TargetedComponent {
  Instrumented() : TargetedComponent(SourcePortConstruction{}) {}
  std::string trace;
  void doUpdates() override {
    trace += 'D';
    if (portablePendingUpdates())
      std::abort();
    TargetedComponent::doUpdates();
  }
  void postDoUpdates() override {
    trace += 'P';
    if (portablePendingUpdates())
      std::abort();
    TargetedComponent::postDoUpdates();
  }
};
struct Child : Core::Portable::Component {
  Instrumented &parent;
  int mutation;
  Child(Instrumented &p, int m) : parent(p), mutation(m) {}
  void onIdle() override {
    parent.trace += 'C';
    if (mutation >= 0)
      parent.portableMarkUpdatesPending(mutation);
  }
};
int main() {
  int pending, mutation;
  while (std::cin >> pending >> mutation) {
    Instrumented product;
    product.portableMarkUpdatesPending(pending);
    product.addChild(new Child(product, mutation));
    product.onIdle();
    std::cout << (product.trace.empty() ? "-" : product.trace) << " "
              << int(product.portablePendingUpdates()) << "\n";
    // Direct pinned provider baseline independently verifies child idle
    // dispatch.
    Instrumented baseline;
    baseline.portableMarkUpdatesPending(pending);
    baseline.addChild(new Child(baseline, mutation));
    baseline.Core::Portable::Component::onIdle();
    std::cout << baseline.trace << " " << int(baseline.portablePendingUpdates())
              << "\n";
  }
}
