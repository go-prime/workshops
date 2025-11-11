import React, { Component } from 'react'

class SampleComponent extends Component {
    state = {
        user: ""
    }

    componentDidUpdate(prevProps, prevState) {
        if(prevProps.id != this.props.id) {
            this.setState('user', fetchUser(this.props.id))
        }
    }

    render() {
        return (
            <p>Hello {this.state.user}</p>
        )
    }
}