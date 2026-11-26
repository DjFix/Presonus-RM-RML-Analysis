#pragma once
#include "core/portable/coreparams.h"
#include "core/portable/coresingleton.h"
#include "core/portable/coreworker.h"
#include "core/public/corestream.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include <string>
#include <vector>

namespace presonus::network {
// Independent source-port provider boundary. Production uses POSIX and CCL;
// tests install an offline capture provider before constructing the singleton.
struct WiFiEnvironment {
  virtual ~WiFiEnvironment() = default;
  virtual int command(const char *) = 0;
  virtual bool exists(const char *) = 0;
  virtual void remove(const char *) = 0;
  virtual bool read(const char *, std::string &) = 0;
  virtual bool write(const char *, const std::string &) = 0;
  virtual bool pipe(const char *, std::string &) = 0;
  virtual void sleep(unsigned) = 0;
  virtual long long milliseconds() = 0;
  virtual std::string tempDirectory() = 0;
  virtual std::vector<std::pair<std::string, std::string>> addresses() = 0;
};
WiFiEnvironment &wifiEnvironment();
void setWiFiEnvironmentForTesting(WiFiEnvironment *);
} // namespace presonus::network

namespace Presonus {
class WIFIManager;
class WIFIManagerDelegate {
public:
  // Vtable order follows original onIdle call sites; method spellings are
  // independent source-port declarations, not recovered ELF identities.
  virtual void wifiStateChanged(WIFIManager *) = 0;
  virtual void wifiAdaptersChanged(WIFIManager *) = 0;

protected:
  ~WIFIManagerDelegate() = default;
};
// Portable representation: fields, returns and CCL adaptation are not ARM ABI.
// Return declarations unencoded in original ordinary function symbols remain
// declaration-pending. Native domains and known exclusions accompany handoff.
// Scan retains the observed empty-SSID/allocation-failure leak behavior;
// cancellation and concurrent manager teardown are outside validated domains.
class WIFIManager : public Core::Portable::Singleton<WIFIManager> {
public:
  struct NetworkItem {
    Core::CStringBuffer<64> bssid, frequency, signal, flags;
    Core::CStringBuffer<64> ssid;
    bool hasFlag(const char *);
  };
  struct PipeTask : Core::Portable::BackgroundTask {
    ~PipeTask() override;
    void setStatus(const char *);
    bool pipeOK(int);
    bool doCommand(const char *, int = -1);
  };
  struct ActiveNetworkTask : PipeTask {
    ~ActiveNetworkTask() override;
    void work() override;
    void setNone();
    bool isEthernet();
  };
  struct ScanWIFITask : PipeTask {
    Core::Vector<NetworkItem *> items;
    ~ScanWIFITask() override;
    void work() override;
  };
  struct JoinNetworkTask : PipeTask {
    Core::CStringBuffer<64> ssid, key;
    bool wep = false, encrypted = false;
    ~JoinNetworkTask() override;
    void work() override;
  };
  struct ReconnectTask : PipeTask {
    ~ReconnectTask() override;
    void work() override;
  };
  struct DisconnectTask : PipeTask {
    ~DisconnectTask() override;
    void work() override;
  };
  struct ConfigNetworkTask : PipeTask {
    Core::CStringBuffer<32> interfaceName, ip, subnet, gateway;
    bool dynamic = false, autoAssign = false;
    ~ConfigNetworkTask() override;
    void work() override;
    void config();
  };
  struct StaticIpFailoverTask : PipeTask {
    Core::CStringBuffer<32> interfaceName, ip;
    ~StaticIpFailoverTask() override;
    void work() override;
  };
  WIFIManager();
  ~WIFIManager() override;
  void terminate();
  void addDelegate(WIFIManagerDelegate *);
  void removeDelegate(WIFIManagerDelegate *);
  void adaptersChanged();
  bool doAdHoc(const char *);
  bool isActive() const;
  NetworkItem *find(const char *);
  void setNetworkItems(Core::Vector<NetworkItem *> &);
  void setStatusMessage(const char *);
  void resetStatusMsg();
  void setActiveNetwork(const char *);
  void setStaticIp(const char *);
  const char *getIP() const;
  const char *getWifiIP() const;
  const char *getEthernetIP() const;
  void updateList(Core::Portable::ListParam *, Core::Portable::ListParam *,
                  Core::Portable::ListParam *, bool);
  void addTask(PipeTask *);
  void doScan(bool);
  void reconnect();
  void disconnect();
  int doJoin(const char *, const char *);
  void configNetwork(const char *, const char *, const char *, const char *,
                     bool, bool);
  bool resetNetwork(const char *, const char *, bool);
  void probeEth0();
  void onIdle();

  // Independent inspection conveniences, outside recovered interface claims.
  int delegateCount() const { return delegates.count(); }
  bool adapterChangePending() const { return adaptersDirty; }
  bool stateChangePending() const { return stateDirty; }
  const char *statusMessage() const { return status.str(); }
  const char *activeNetwork() const { return active.str(); }
  int lastError() const { return retryState; }
  const char *staticIP() const { return staticIp.str(); }
  const char *scratchFile() const { return scratch.str(); }

private:
  // Independent replay probe; does not establish original declaration/layout.
  friend struct WiFiRecoveryProbe;
  Core::Threads::Lock lock;
  int networkID = 0, retryState = 0;
  bool stateDirty = false, adaptersDirty = false;
  long long scanDeadline = 0, otherDeadline = 0;
  Core::CStringBuffer<256> status, active;
  Core::Vector<NetworkItem *> items;
  Core::Vector<WIFIManagerDelegate *> delegates;
  Core::Portable::BackgroundWorker *worker;
  Core::CStringBuffer<32> staticIp;
  Core::CStringBuffer<128> scratch;
};
} // namespace Presonus
