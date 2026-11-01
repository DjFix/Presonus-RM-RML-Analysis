#include "presonus/LinkableComponent.hpp"
#include <array>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>
using Presonus::LinkableComponent;
struct OracleBoundary final : Presonus::linkable_port::Boundary {
  std::array<LinkableComponent *, 4> nodes{};
  std::array<int, 4> queryable{};
  std::vector<long long> trace;
  Presonus::linkable_port::State *states = nullptr;
  void snapshot() {
    for (int i = 0; i < 4; ++i)
      trace.insert(trace.end(),
                   {id(states[i].partner), states[i].slave, states[i].enabled});
  }
  int id(LinkableComponent *p) {
    if (!p)
      return -1;
    for (int i = 0; i < 4; ++i)
      if (nodes[i] == p)
        return i;
    throw 1;
  }
  LinkableComponent *query(LinkableComponent &n, std::uint32_t tag) override {
    trace.insert(trace.end(), {0, id(&n), tag, 0});
    snapshot();
    return queryable[id(&n)] ? &n : nullptr;
  }
  void remove(LinkableComponent &n) override {
    trace.insert(trace.end(), {1, id(&n), 0, 0});
    snapshot();
  }
  void set(LinkableComponent &n, LinkableComponent &p, bool b) override {
    trace.insert(trace.end(), {2, id(&n), id(&p), b});
    snapshot();
  }
  void master(LinkableComponent &n, LinkableComponent &p) override {
    trace.insert(trace.end(), {3, id(&n), id(&p), 0});
    snapshot();
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1]);
  if (!f)
    return 2;
  std::string line;
  int cases = 0;
  while (std::getline(f, line)) {
    std::istringstream in(line);
    int method, peer, flag;
    in >> method >> peer >> flag;
    OracleBoundary b;
    std::array<Presonus::linkable_port::State, 4> states{};
    b.states = states.data();
    std::array<std::unique_ptr<LinkableComponent>, 4> nodes;
    std::array<std::vector<LinkableComponent *>, 4> children;
    for (int i = 0; i < 4; ++i) {
      nodes[i] = std::make_unique<LinkableComponent>(states[i], b);
      b.nodes[i] = nodes[i].get();
    }
    for (int i = 0; i < 4; ++i) {
      int partner, slave, enabled, count;
      in >> partner >> slave >> enabled >> b.queryable[i] >> count;
      states[i].partner = partner < 0 ? nullptr : b.nodes[partner];
      states[i].slave = slave;
      states[i].enabled = enabled;
      while (count--) {
        int x;
        in >> x;
        children[i].push_back(x < 0 ? nullptr : b.nodes[x]);
      }
      states[i].children = children[i].data();
      states[i].count = children[i].size();
    }
    int result = -1;
    switch (method) {
    case 0:
      nodes[0]->linkAsSlave(*nodes[peer]);
      break;
    case 1:
      nodes[0]->setLink(*nodes[peer], flag);
      break;
    case 2:
      nodes[0]->removeLink();
      break;
    case 3:
      nodes[0]->setLinkEnabled(flag);
      break;
    case 4:
      result = nodes[0]->isLinked();
      break;
    default:
      return 2;
    }
    bool good = true;
    for (int i = 0; i < 4; ++i) {
      int p, s, e;
      in >> p >> s >> e;
      good &= p == b.id(states[i].partner) && s == states[i].slave &&
              e == states[i].enabled;
    }
    int expected, count;
    in >> expected >> count;
    good &= result == expected && count == static_cast<int>(b.trace.size());
    for (int i = 0; i < count; ++i) {
      long long v;
      in >> v;
      good &= i < static_cast<int>(b.trace.size()) && b.trace[i] == v;
    }
    if (!in || !good) {
      std::cerr << "Mismatch case " << cases << '\n';
      return 1;
    }
    ++cases;
  }
  std::cout << "passed " << cases << " native fixture cases\n";
  return cases == 480 ? 0 : 1;
}
