import React, { useState } from 'react'

const SampleComponent ({id}) => {
    const [user, setUser] = useState("")
    React.useEffect(() => {
        if(id)
            setUser(fetchUser(id)); // ephemeral import
    }, [id])
    return (
        <p>Hello {user}</p>
    )
}