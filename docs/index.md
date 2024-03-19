# Scistream Documentation

Welcome to the Scistream Documentation. As in the case with any on-going project, these docs may fall out of sync with the project, but we’ll try our best to keep them accurate.

![Scientific Instrument needs to connect to analysis compute cluster in a different institution](figures/scistream-arch.png "Scistream Architecture")

Scistream is a framework and toolkit that attempts to tackle the problem of enabling high-speed(+100Gbps), memory-to-memory data streaming between scientific instruments and remote computing facilities. It addresses the challenges of streaming data in scientific environments where the data producers (e.g., scientific instruments) and consumers (e.g., analysis applications) are often in different institutions with different security domains.

For example, SciStream can enable real-time data analysis for synchrotron light source experiments, where the detector generates data at high rates, and the analysis needs to be performed on a remote high-performance computing (HPC) cluster. Similarly, in cosmology simulations, SciStream can facilitate streaming of simulation data to a remote facility for real-time visualization and analysis.

SciStream tackles these challenges by providing a middlebox-based architecture with control protocols that establish authenticated and transparent connections between the data producer and consumer, while efficiently bridging the different security domains. It integrates with existing authentication and authorization systems, such as Globus Auth, to ensure secure communication between the participating facilities.

## Key Features

- High-speed memory-to-memory data streaming (100Gbps+)
- Bridging of security domains between scientific instruments and remote computing facilities
- Integration with existing authentication and authorization systems (e.g., Globus Auth)
- Transparent and efficient connections between data producers and consumers
- Agnostic to data streaming libraries and applications

For a more detailed explanation of the SciStream protocol and components, please refer to the Vocabulary of Messages and Procedure Rules sections.

If you want to learn more about Scistream, please check the ["What is Scistream" page](scistream/README.md). For further detail review our papers: [HPDC'22](https://dl.acm.org/doi/abs/10.1145/3502181.3531475) and [INDIS'22](https://ieeexplore.ieee.org/document/10024674).

## Documentation

   - [What is Scistream?](scistream/README.md)
   - [Getting started](quickstart.md)
   - [User Guide](guides/user.md)
   - [Authentication Guide](guides/auth.md)
   - [Developer Guide](guides/dev.md)

## Project layout

    poetry.lock         # Explicitly documents all Python dependencies using Poetry
    pyproject.toml      # Python dependencie: Poetry equivalent to requirements.txt
    mkdocs.yml          # Documentation configuration file.
    docs/
      index.md          # The documentation homepage.
      ...               # Other markdown pages, images and other files.
    deploy/
      setup.sh          # Installation script
    src/
      proto/            # GRPC protocol specifications
      appcontroller.py  # Application controller reference implementations
      s2cs.py           # Scistream Control Server implementation
      s2ds.py           # Scistream Dataplane server plugin
      s2uc.py           # Scistream User Client implementation
      utils.py          # Supporting code
      ...               # other files
    tests/
      test_s2cs.py      # pytest tests
      ...               # other tests

### How Scistream works

1. The user authenticates with the participating facilities and requests a streaming job through the SciStream User Client (S2UC).
2. The SciStream Control Servers (S2CS) at the producer and consumer facilities negotiate the connection details and allocate the necessary resources.
3. The SciStream Data Servers (S2DS) establish authenticated and transparent connections between the data producer and consumer.
4. The data producer streams data to the consumer through the SciStream infrastructure, enabling real-time analysis and visualization.

#### Collaboration Diagram

![alt text](figures/collaboration-diagram.png "SciStream collaboration diagram")

#### Sequence Diagram

![alt text](figures/scistream-protocol-simple.png "SciStream sequence diagram")
