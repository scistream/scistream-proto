# SciStream User Client (S2UC)

The S2UC interacts with users to initialize, start, monitor, and terminate a streaming pipeline.
It can run as either a native application or cloud-based service.
To easily run on different platforms, as well as to use OAuth redirect for enabling users to authenticate directly with the campus authentication systems and for acquiring the X.509 certificates in a transparent way, we plan to architect it with a web-based model so that users can interact with system by using a browser.
We will provide a web API so that user can also run S2UC natively.
We also plan to develop S2UC as a cloud-based service so that it can be easily deployed.
To this end, we plan to implement the back-end components with Python and C/C++ and the web front-end components with libraries that utilize JavaScript, HTML, and CSS.
