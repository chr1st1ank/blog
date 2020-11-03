## Composing a complex kubernetes configuration with kustomize

### What is kustomize

### Target Configuration Structure
Multiple dimensions:
- environment (dev/test/prod):
    Different sizing, additional ingress routes
- target cluster (eu/us):
    Ingress routes
    Sizing
- application variant (per country for example with a separate db backend?):
    Database backend
    base path

```mermaid
graph LR;
Base(Base) --> DE(DE)
Base --> FR(FR)
DE --> Dev
FR --> Dev2(Dev)
DE --> Prod(Prod)
FR --> Prod2(Prod)
Dev --> ceu(EU Cluster)
Dev --> cus(US Cluster)
Dev2 --> ceu2(EU Cluster)
Dev2 --> cus2(US Cluster)
Prod --> ceu3(EU Cluster)
Prod --> cus3(US Cluster)
Prod2 --> ceu4(EU Cluster)
Prod2 --> cus5(US Cluster)
```
Exponential growth of configurations

### Implementation

### Summary

The code is available on github...
