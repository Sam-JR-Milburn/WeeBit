
### Vision and Scope 

#### What is WeeBit? 

WeeBit is a no-frills link shortener web service in Python and React. 

Users will be able to submit a hyperlink to the service and return a compact ('wee') redirection link ('bit'). 

If the link does not yet exist in the system, it will normalise and sanitise the link to remove trackers, and generate the referrer link. 
if it does, you'll return the existing 'wee bit'. 

#### Core Objectives
- Deliver low-latency redirection with simple efficient caching
- Simply yet intelligently inform caching by collecting link-usage statistics
- Consistent link normalisation and deduplication

#### Out Of Scope (v1.0)

 - User logins
 - User analytics dashboard
 - Liveness checking

### Functional Requirements

#### FR1 - Submit a link to be stored
>
>Request: POST **/api/link**
>>Send a link (JSON in body) to be normalised and stored for access. 
>>
>>This includes a "include tracking params" flag, that is false by default. 
>
>Response: 201 Created
>>Returned if the link has been normalised and stored and is new. 
>>
>>Returns the Short Referrer Code. 
>>
>>Transformed into a clickable link client-side. 
>
>Response: 200 OK
>>Returned if the link has been normalised and stored but already exists. 
>>
>>Returns the Short Referrer Code. 
>>
>>Transformed into a clickable link client-side. 
>
>Response: 422 Unprocessable Entity
>>If the link is invalid and fails validation rules. (eg. 'file://' or 'javascript:')
>
>Response: 400 Bad Request 
>>
>>If the link is invalid for some other reason (format, not liveness). 
>>
>>Triggers an error page client-side.

#### FR2 - Get redirected with the Short Referrer Code

>Request: GET **/{SRC}**
>
>Response: 307 Temporary Redirect 
>>If the SRC exists in the database. 
>>
>>Redirects to the normalised link.
>
>Response: 404 Not Found
>>If the SRC doesn't exist in the database. 
>>
>>Triggers an error page client-side.

### System Architecture and Design

#### Normalisation Pipeline

Links must pass through a chain of normalisation modules in a pipeline. 
Links must:
 - structure the URL as HTTP/S only (default scheme), 
 - have their parameter keys ordered alphabetically, 
 - be lowercase in their scheme + hostname, 
 - be internationalized (eg. Punycode), 
 - have empty query params standardised,
 - respect RFC 3986 (uppercase percent-encodings)

Links optionally: 
 - strip tracking params 


#### Short Referrer Code Generation

Normalised URLs need to be hashed with SHA256. 
Because of the avalanche effect, taking a slice of the hash doesn't compromise it's randomness. 

We convert the entire SHA256 hash into base62 and take a short slice from the beginning as the **Short Referrer Code**. 

Why **base62**? 
Base62 is used because it uses the 0-9 digits, the 26 lowercase latin characters, and the 26 uppercase characters. 
It's human-readable and URL safe. (no '+', '-', '=' padding or special characters) 

By default, we'll take a slice of the first **7** characters of the base62 transformed hash and check for collisions. 

7-characters gives us a 50% collision threshold at 2.2 million links, per the birthday paradox formula. 

**How are collisions handled?**


Collisions will be resolved by checking the SRC and the normalised URL at the end of the link save processing. 

If you go to save a URL and the SRC already exists, we check: 
 - If the normalised URL matches the saved URL, then we simply return the SRC. 
 - The normalised URL doesn't match, we have an SRC collision. We take an n+1 slice of the base62 string. 
 
 The n+1 slice increments until there's no collision or we hit the limit at 9 characters. 
 10 and beyond is infeasible. 

#### Caching

The API will be connected to a Redis cache for first-lookup. 
The SRC-to-Normalised-URL will be the format. 

When a link is saved, it's cached for 15 minutes. 
When a link is accessed, 5 minutes are added to its cache time, or set if it's out-of-cache. 